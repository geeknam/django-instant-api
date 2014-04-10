from django.core.management.sql import custom_sql_for_model, emit_post_sync_signal
from django.core.management.color import no_style
from django.db import connections, router, transaction, models, DEFAULT_DB_ALIAS
from django.utils.datastructures import SortedDict
from django.utils.encoding import smart_unicode
from django.contrib.contenttypes.models import ContentType

def create(model, using):
    ''' Mostly lifted from django.core.management.commands.syncdb'''
    
    opts = model._meta

    # Get database connection and cursor
    db = using or DEFAULT_DB_ALIAS
    connection = connections[db]
    cursor = connection.cursor()

    # Get a list of already installed *models* so that references work right.
    tables = connection.introspection.table_names()
    seen_models = connection.introspection.installed_models(tables)
    created_models = set()
    pending_references = {}
    
    # Abort if the table we're going to create already exists
    if opts.db_table in tables:
        return
        
    # Build the manifest of apps and models that are to be synchronized
    all_models = [
        (app.__name__.split('.')[-2],
            [m for m in models.get_models(app, include_auto_created=True)
            if router.allow_syncdb(db, m)])
        for app in models.get_apps()
    ]
    def model_installed(model):
        opts = model._meta
        converter = connection.introspection.table_name_converter
        return not ((converter(opts.db_table) in tables) or
            (opts.auto_created and converter(opts.auto_created._meta.db_table) in tables))

    manifest = SortedDict(
        (app_name, filter(model_installed, model_list))
        for app_name, model_list in all_models
    )

    # Get create SQL
    sql, references = connection.creation.sql_create_model(model, no_style(), seen_models)
    seen_models.add(model)
    created_models.add(model)
    for refto, refs in references.items():
        pending_references.setdefault(refto, []).extend(refs)
        if refto in seen_models:
            sql.extend(connection.creation.sql_for_pending_references(refto, no_style(), pending_references))
    sql.extend(connection.creation.sql_for_pending_references(model, no_style(), pending_references))
    for statement in sql:
        cursor.execute(statement)
    tables.append(connection.introspection.table_name_converter(model._meta.db_table))

    # Create content_type
    try:
        ct = ContentType.objects.get(app_label=opts.app_label,
                                     model=opts.object_name.lower())
    except ContentType.DoesNotExist:
        ct = ContentType(name=smart_unicode(opts.verbose_name_raw),
            app_label=opts.app_label, model=opts.object_name.lower())
        ct.save()

    # Commit changes to the database
    transaction.commit_unless_managed(using=db)
    
    # Send the post_syncdb signal, so individual apps can do whatever they need
    # to do at this point.
    emit_post_sync_signal(created_models, 0, False, db)

    # The connection may have been closed by a syncdb handler.
    cursor = connection.cursor()

    # Install SQL indicies for all newly created models
    for app_name, model_list in manifest.items():
        for model in model_list:
            if model in created_models:
                index_sql = connection.creation.sql_indexes_for_model(model, no_style())
                if index_sql:
                    try:
                        for sql in index_sql:
                            cursor.execute(sql)
                    except Exception, e:
                        sys.stderr.write("Failed to install index for %s.%s model: %s\n" % \
                                            (app_name, model._meta.object_name, e))
                        transaction.rollback_unless_managed(using=db)
                    else:
                        transaction.commit_unless_managed(using=db)


