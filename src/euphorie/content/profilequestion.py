from .. import MessageFactory as _
from .behaviour.richdescription import IRichDescription
from .behaviour.uniqueid import get_next_id
from .behaviour.uniqueid import INameFromUniqueId
from .fti import check_fti_paste_allowed
from .interfaces import IQuestionContainer
from .module import ConstructionFilter
from .module import IModule
from .module import item_depth
from .module import tree_depth
from .risk import IRisk
from .utils import StripMarkup
from five import grok
from plone.app.dexterity.behaviors.metadata import IBasic
from plone.directives import dexterity
from plone.directives import form
from plone.indexer import indexer
from plonetheme.nuplone.skin.interfaces import NuPloneSkin
from plonetheme.nuplone.z3cform.form import FieldWidgetFactory
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from zope import schema
from zope.component import getMultiAdapter
from zope.interface import implements
import sys


grok.templatedir("templates")

TextSpan7 = FieldWidgetFactory("z3c.form.browser.text.TextFieldWidget",
        klass="span-7")


class IProfileQuestion(form.Schema, IRichDescription, IBasic):
    """Survey Profile question.

    A profile question is used to determine if parts of a survey should
    be skipped, or repeated multiple times.
    """
    question = schema.TextLine(
        title=_('label_profilequestion_question', default=u'Question'),
        description=_(u'This question must ask the user if this profile '
                      u'applies to them.'),
        required=True)

    label_multiple_present = schema.TextLine(
        title=_(u'Multiple item question'),
        required=True,
        description=_(u'This question must ask the user if the service is '
                      u'offered in more than one location.'),
    )
    form.widget(
        label_multiple_present='euphorie.content.profilequestion.TextSpan7')

    label_single_occurance = schema.TextLine(
        title=_(u'Single occurance prompt'),
        description=_(u'This must ask the user for the name of the '
                      u'relevant location.'),
        required=True)
    form.widget(
        label_single_occurance='euphorie.content.profilequestion.TextSpan7')

    label_multiple_occurances = schema.TextLine(
        title=_(u'Multiple occurance prompt'),
        description=_(u'This must ask the user for the names of all '
                      u'relevant locations.'),
        required=True)
    form.widget(
        label_multiple_occurances='euphorie.content.profilequestion.TextSpan7')


class ProfileQuestion(dexterity.Container):
    implements(IProfileQuestion, IQuestionContainer)

    question = None
    image = None
    optional = False

    def _get_id(self, orig_id):
        """Pick an id for pasted content."""
        frame = sys._getframe(1)
        ob = frame.f_locals.get('ob')
        if ob is not None and INameFromUniqueId.providedBy(ob):
            return get_next_id(self)
        return super(ProfileQuestion, self)._get_id(orig_id)

    def _verifyObjectPaste(self, object, validate_src=True):
        super(ProfileQuestion, self)._verifyObjectPaste(object, validate_src)
        if validate_src:
            check_fti_paste_allowed(self, object)
            if IQuestionContainer.providedBy(object):
                my_depth = item_depth(self)
                paste_depth = tree_depth(object)
                if my_depth + paste_depth > ConstructionFilter.maxdepth:
                    raise ValueError('Pasting would create a too deep structure.')


@indexer(IProfileQuestion)
def SearchableTextIndexer(obj):
    return " ".join([obj.title,
                     StripMarkup(obj.description)])


class View(grok.View):
    grok.context(IProfileQuestion)
    grok.require("zope2.View")
    grok.layer(NuPloneSkin)
    grok.template("profilequestion_view")
    grok.name("nuplone-view")

    def _morph(self, child):
        state = getMultiAdapter((child, self.request),
                name="plone_context_state")
        return {'id': child.id,
                'title': child.title,
                'url': state.view_url()}

    def update(self):
        self.modules = [self._morph(child)
                        for child in self.context.values()
                        if IModule.providedBy(child)]
        self.risks = [self._morph(child) for child in self.context.values()
                      if IRisk.providedBy(child)]


class AddForm(dexterity.AddForm):
    grok.context(IProfileQuestion)
    grok.name('euphorie.profilequestion')
    grok.require('euphorie.content.AddNewRIEContent')
    grok.layer(NuPloneSkin)
    form.wrap(True)

    schema = IProfileQuestion
    template = ViewPageTemplateFile('templates/profilequestion_add.pt')

    @property
    def label(self):
        return _(u"Add Profile question")
