from django.conf import settings
from django.utils.translation import ugettext

from south.signals import post_migrate

from merengue.plugins.models import RegisteredPlugin
from merengue.plugins.utils import get_plugin_config
from merengue.registry import register, is_registered
from merengue.registry.items import RegistrableItem

PLUG_CACHE_KEY = 'plug__loaded'


class Plugin(RegistrableItem):
    model = RegisteredPlugin
    url_prefixes = ()

    @classmethod
    def get_category(cls):
        return 'plugin'

    @classmethod
    def get_actions(cls):
        return [] # to override in plugins

    @classmethod
    def get_blocks(cls):
        return [] # to override in plugins

    @classmethod
    def get_viewlets(cls):
        return [] # to override in plugins

    @classmethod
    def post_actions(cls):
        pass

    @classmethod
    def section_models(cls):
        return [] # to override in plugins

    @classmethod
    def section_register_hook(cls, site_related, model):
        pass

    @classmethod
    def get_model_admins(cls):
        return [] # to override in plugins


def register_plugin(plugin_dir):
    plugin_config = get_plugin_config(plugin_dir)
    if plugin_config:
        if not is_registered(plugin_config):
            register(plugin_config)
        plugin = RegisteredPlugin.objects.get_by_item(plugin_config)
        plugin.name = getattr(plugin_config, 'name', plugin_dir)
        plugin.directory_name = plugin_dir
        plugin.description = getattr(plugin_config, 'description', '')
        plugin.version = getattr(plugin_config, 'version', '')
        plugin.required_apps = getattr(plugin_config, 'required_apps',
                                       None)
        plugin.required_plugins = getattr(plugin_config,
                                          'required_plugins',
                                          None)
        plugin.save()
        return plugin
    return None


def enable_active_plugins():
    from merengue.plugins.utils import enable_plugin, get_plugin_module_name
    for plugin_registered in RegisteredPlugin.objects.actives():
        enable_plugin(get_plugin_module_name(plugin_registered.directory_name))


def active_default_plugins(*args, **kwargs):
    if kwargs['app'] == 'section':
        interactive = kwargs.get('interactive', None)
        # register required plugins
        for plugin_dir in settings.REQUIRED_PLUGINS:
            plugin = register_plugin(plugin_dir)
            plugin.installed = True
            plugin.active = True
            from merengue.section.models import Menu
            portal_menu, created = Menu.objects.get_or_create(slug='portal_menu')
            for lang_code, lang_text in settings.LANGUAGES:
                setattr(portal_menu, 'name_%s' % lang_code, ugettext('portal menu'))
            portal_menu.save()
            plugin.save()


post_migrate.connect(active_default_plugins)
