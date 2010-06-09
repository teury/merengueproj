from django.conf import settings
from django.contrib import admin
from django.forms.models import save_instance
from django.forms.util import ValidationError
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ugettext

from transmeta import get_fallback_fieldname

from merengue.base.admin import BaseAdmin, BaseContentAdmin, RelatedModelAdmin, \
                                BaseOrderableAdmin, OrderableRelatedModelAdmin
from merengue.base.admin import set_field_read_only
from merengue.section.fields import CSSValidatorField
from merengue.section.forms import MenuAdminModelForm
from merengue.section.models import (Menu, Section,
                                     BaseLink, AbsoluteLink, ContentLink, ViewletLink,
                                     Document, DocumentSection, CustomStyle,
                                     SectionRelatedContent)
from merengue.section.widgets import SearchFormOptionsWidget


class BaseSectionAdmin(BaseOrderableAdmin):
    sortablefield = 'order'
    ordering = ('order', )
    list_display = ('name', 'slug', )
    list_display_links = ('name', )
    html_fields = ()
    removed_fields = ('description', )
    prepopulated_fields = {'slug': (get_fallback_fieldname('name'), )}

    def get_form(self, request, obj=None, **kwargs):
        form = super(BaseSectionAdmin, self).get_form(request, obj, **kwargs)
        if 'main_content' in form.base_fields.keys():
            field = form.base_fields['main_content']
            qs = field.queryset
            if not obj:
                qs = qs.model.objects.get_empty_query_set()
            else:
                qs = qs.filter(basesection=obj)

            # Como Document no esta registrado en el admin site, no tiene
            # sentido mostrar este campo si no tiene opciones ya que no
            # se pueden crear nuevos documentos desde aqui
            if qs.count():
                field.queryset = qs
            else:
                form.base_fields.pop('main_content')
        return form


class AbsoluteLinkAdmin(BaseAdmin):
    list_display = ('url', )


class ContentLinkAdmin(BaseAdmin):
    list_display = ('content', )


class ViewletLinkAdmin(BaseAdmin):
    list_display = ('viewlet', )


class SectionAdmin(BaseSectionAdmin):

    def render_change_form(self, request, context, add=False, change=False, form_url='', obj=None):
        context['change_form_section'] = True
        return super(SectionAdmin, self).render_change_form(request, context, add, change, form_url, obj)


class SectionContentAdmin(OrderableRelatedModelAdmin):
    related_field = 'basesection'
    sortablefield = 'order'

    def custom_relate_content(self, request, obj, form, change):
        if not change:
            section_relatedcontent_rel = SectionRelatedContent.objects.create(
                basesection=self.basecontent,
                basecontent=obj)

    def get_relation_obj(self, through_model, obj):
        return through_model.objects.get(basesection=self.basecontent, basecontent=obj)


class CustomStyleRelatedModelAdmin(RelatedModelAdmin):
    tool_name = 'style'
    tool_label = _('custom style')
    related_field = 'basesection'
    one_to_one = True

    def formfield_for_dbfield(self, db_field, **kwargs):
        formfield = super(CustomStyleRelatedModelAdmin, self).formfield_for_dbfield(db_field, **kwargs)
        if db_field.name == 'css_chunk':
            formfield = CSSValidatorField(db_field.name, kwargs['request'])
            formfield.help_text = _('Custom style for the section. Can you use the variables $media_url and $theme_url')
        return formfield

    def has_delete_permission(self, request, obj=None):
        return False


class DocumentAdmin(BaseContentAdmin):
    list_display = ('name', 'slug', 'status', )
    list_filter = ('status', )
    html_fields = ('description', 'body', )
    prepopulated_fields = {'slug': (get_fallback_fieldname('name'), )}
    actions = BaseAdmin.actions + ['set_as_published', 'set_as_draft']


class DocumentRelatedModelAdmin(SectionContentAdmin, DocumentAdmin):
    tool_name = 'documents'
    tool_label = _('documents')

    def get_form(self, request, obj=None, **kwargs):
        form = super(DocumentRelatedModelAdmin, self).get_form(request, obj, **kwargs)
        if obj and obj.permanent and 'slug' in form.base_fields.keys():
            set_field_read_only(form.base_fields['slug'], 'slug', obj)
        return form

    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == 'search_form':
            from searchform.registry import search_form_registry
            db_field._choices = search_form_registry.get_choices()

        formfield = super(DocumentRelatedModelAdmin, self).formfield_for_dbfield(db_field, **kwargs)
        if db_field.name == 'search_form_filters':
            formfield.widget = SearchFormOptionsWidget()

        return formfield


class BaseLinkInline(admin.TabularInline):

    def get_fieldsets(self, request, obj=None):
        if self.declared_fieldsets:
            return self.declared_fieldsets
        formset = self.get_formset(request)
        if not formset:
            return []
        else:
            form = formset.form
            return [(None, {'fields': form.base_fields.keys()})]

    def get_formset(self, request, obj=None, **kwargs):
        formset = super(BaseLinkInline, self).get_formset(request, obj=None, **kwargs)
        if obj:
            try:
                if not isinstance(obj.baselink.real_instance, self.model):
                    return None
            except BaseLink.DoesNotExist:
                pass

        def save_new(formset_self, form, commit=True):
            fk_attname = formset_self.fk.get_attname()
            kwargs = {fk_attname: formset_self.instance.pk}
            new_obj = formset_self.model(**kwargs)
            if fk_attname == formset_self._pk_field.attname:
                exclude = [formset_self._pk_field.name]
            else:
                exclude = []
            if 'baselink_ptr' in form.cleaned_data and not form.cleaned_data['baselink_ptr']:
                del(form.cleaned_data['baselink_ptr'])
            return save_instance(form, new_obj, exclude=exclude, commit=commit)

        def clean(formset_self):
            data=formset_self.data
            if data.get('contentlink-0-content', None) and data.get('absolutelink-0-url', None) or \
               data.get('viewletlink-0-viewlet', None) and data.get('contentlink-0-content', None) or \
               data.get('viewletlink-0-viewlet', None) and data.get('absolutelink-0-content', None):
                raise ValidationError(_('Sorry you can not select two or more options simultaneously for this menu. Fulfill just one.'))
        formset.save_new = save_new
        formset.clean = clean
        return formset


class AbsoluteLinkInline(BaseLinkInline):
    model = AbsoluteLink
    max_num = 1
    verbose_name = _('Menu Absolute Link')
    verbose_name_plural = _('Menu Absolute Links')

    def _media(self):
        from django import forms

        #js = ['%sjs/tiny_mce_internal_links/no_tiny_mce_internal_links.js' % settings.MEDIA_URL]
        js = []
        if self.prepopulated_fields:
            js.append('%sjs/urlify.js' % settings.ADMIN_MEDIA_PREFIX)
        if self.filter_vertical or self.filter_horizontal:
            js.extend(['%sjs/SelectBox.js' % settings.ADMIN_MEDIA_PREFIX,
                       '%sjs/SelectFilter2.js' % settings.ADMIN_MEDIA_PREFIX])
        return forms.Media(js=js)
    media = property(_media)

    def formfield_for_dbfield(self, db_field, **kwargs):
        field = super(AbsoluteLinkInline, self).formfield_for_dbfield(db_field, **kwargs)
        if db_field.name == 'url':

            def clean(value):
                return value
            field.clean=clean
        return field


class ContentLinkInline(BaseLinkInline):
    model = ContentLink
    max_num = 1
    verbose_name = _('Menu Content Link')
    verbose_name_plural = _('Menu Content Links')

    def get_formset(self, request, obj=None, **kwargs):
        formset = super(ContentLinkInline, self).get_formset(request, obj, **kwargs)
        if not formset:
            return formset
        form = formset.form
        if 'content' in form.base_fields.keys():
            qs = form.base_fields['content'].queryset
            admin_model = getattr(self, 'admin_model', None)
            if admin_model:
                qs = qs.filter(basesection=admin_model.basecontent)
            form.base_fields['content'].queryset = qs
        return formset


class ViewletLinkInline(BaseLinkInline):
    model = ViewletLink
    max_num = 1
    verbose_name = _('Menu Viewlet Link')
    verbose_name_plural = _('Menu Viewlet Links')


class MenuAdmin(BaseAdmin):
    list_display = ('level', 'display_move_to', 'name', 'slug', )
    list_display_links = ('name', )
    prepopulated_fields = {'slug': (get_fallback_fieldname('name'), )}
    ordering=('lft', )
    actions = []
    inherit_actions = False
    inlines = [AbsoluteLinkInline, ContentLinkInline, ViewletLinkInline]
    form = MenuAdminModelForm

    def __init__(self, *args, **kwargs):
        super(MenuAdmin, self).__init__(*args, **kwargs)
        self.old_inline_instances = [instance for instance in self.inline_instances]

    def display_move_to(self, menu):
        hidden = u'<input type="hidden" class="thisMenu" name="next" value="%s" />' % menu.id
        init_move = u'<a href="#" class="initMoveMenu" title="%(title)s">%(title)s</a>' % {'title': ugettext(u'Move this menu')}
        cancel_move = u'<a href="#" class="cancelMoveMenu hide" title="%(title)s">%(title)s</a>' % {'title': ugettext(u'Cancel move')}
        options = (
            u'<li><a href="#" class="insertPrev" title="%(title)s">%(title)s</a></li>' % {'title': ugettext(u'Before')},
            u'<li><a href="#" class="insertNext" title="%(title)s">%(title)s</a></li>' % {'title': ugettext(u'After')},
            u'<li><a href="#" class="insertChild" title="%(title)s">%(title)s</a></li>' % {'title': ugettext(u'Child')},
            )
        options = u'<ul class="insertOptions hide">' + u''.join(options) + u'</ul>'
        return mark_safe('%s%s%s%s' % (hidden, init_move, cancel_move, options))
    display_move_to.allow_tags=True

    def get_formsets(self, request, obj=None):
        self.inline_instances = []
        res = []
        for inline in self.old_inline_instances:
            formset = inline.get_formset(request, obj)
            if formset:
                self.inline_instances.append(inline)
                res.append(formset)
        return res

    def get_form(self, request, obj=None, **kwargs):
        form = super(MenuAdmin, self).get_form(request, obj, **kwargs)
        form.section = getattr(self, 'basecontent', None)
        return form

    def move_menus(self, request):
        source_id = request.GET.pop('source', None)
        target_id = request.GET.pop('target', None)
        movement = request.GET.pop('movement', None)
        if not source_id and not target_id and not movement:
            return

        if source_id and target_id and movement:
            query = self.queryset(request)
            try:
                source_menu = query.get(id=source_id[0])
                target_menu = query.get(id=target_id[0])
                source_menu.move_to(target_menu, movement[0])
                return source_id[0]
            except:
                pass

    def changelist_view(self, request, extra_context={}):
        source = self.move_menus(request)
        media = self.media
        media.add_js([settings.MEDIA_URL + "merengue/js/jquery-ui-1.8.dragdrop.min.js"])
        media.add_js([settings.MEDIA_URL + "merengue/js/section/CollapsableMenuTree.js"])
        media.add_js([settings.MEDIA_URL + "merengue/js/section/OrderableMenuTree.js"])
        extra_context.update({'media': media.render(),
                              'moved_source': source})
        return super(MenuAdmin, self).changelist_view(
                                                        request, extra_context)


class BaseSectionMenuRelatedAdmin(MenuAdmin, RelatedModelAdmin):
    change_list_template = "admin/section/menu/change_list.html"

    def get_menu(self, request, basecontent=None):
        return super(BaseSectionMenuRelatedAdmin, self).queryset(request, basecontent).get()

    def get_section_docs(self, request):
        section = getattr(self.get_menu(request), self.related_field)
        return section.content_set.all()

    def get_form(self, request, obj=None, **kwargs):
        form = super(BaseSectionMenuRelatedAdmin, self).get_form(
                                                    request, obj, **kwargs)
        if 'parent' in form.base_fields.keys():
            qs = form.base_fields['parent'].queryset
            qs = qs.filter(tree_id=self.get_menu(request).tree_id, level__gt=0)
            if obj:
                qs = qs.exclude(pk=obj.pk)
            form.base_fields['parent'].queryset = qs
        return form

    def queryset(self, request, basecontent=None):
        menu = self.get_menu(request, basecontent)
        if not menu:
            return Menu.tree.get_empty_query_set()
        else:
            return Menu.tree.filter(tree_id=menu.tree_id, level__gt=0)

    def save_model(self, request, obj, form, change):
        if not obj.parent:
            obj.parent = self.get_menu(request)
        super(BaseSectionMenuRelatedAdmin, self).save_model(
                                                request, obj, form, change)


class MainMenuRelatedAdmin(BaseSectionMenuRelatedAdmin):
    tool_name = 'mainmenu'
    tool_label = _('main menu')
    related_field = 'main_menu_section'


class PortalMenuAdmin(MenuAdmin):
    tool_name = 'portalmenu'
    tool_label = _('portal menu')
    related_field = 'parent'

    def queryset(self, request, basecontent=None):
        basecontent = Menu.tree.get(slug=settings.MENU_PORTAL_SLUG)
        return basecontent.get_descendants()

    def get_form(self, request, obj=None, **kwargs):
        form = super(PortalMenuAdmin, self).get_form(
                                                    request, obj, **kwargs)
        if 'parent' in form.base_fields.keys():
            qs = form.base_fields['parent'].queryset
            root_menu = Menu.tree.get(slug=settings.MENU_PORTAL_SLUG)
            descendants = root_menu.get_descendants()
            qs = descendants and qs.filter(pk__in=descendants.values('pk').query) or descendants
            form.base_fields['parent'].queryset = qs
        return form

    def save_form(self, request, form, change):
        menu = form.save(commit=False)
        if not getattr(menu, self.related_field, None):
            basecontent = Menu.objects.get(slug=settings.MENU_PORTAL_SLUG)
            setattr(menu, self.related_field, basecontent)
        return menu


class DocumentSectionModelAdmin(BaseAdmin):
    ordering = ('position', )
    html_fields = ('body', )


class DocumentSectionRelatedModelAdmin(RelatedModelAdmin):
    tool_name = 'document_sections'
    tool_label = _('document sections')
    ordering = ('position', )
    html_fields = ('body', )
    related_field = 'document'


def register(site):
    site.register(Section, SectionAdmin)
    site.register(Menu, PortalMenuAdmin)
    site.register_related(Document, DocumentRelatedModelAdmin, related_to=Section)
    site.register_related(CustomStyle, CustomStyleRelatedModelAdmin, related_to=Section)
    site.register_related(Menu, MainMenuRelatedAdmin, related_to=Section)
    site.register_related(DocumentSection, DocumentSectionRelatedModelAdmin, related_to=Document)
