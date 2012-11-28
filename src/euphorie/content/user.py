import re
from Acquisition import aq_base
from Acquisition import aq_chain
from Acquisition import aq_inner
from Acquisition import aq_parent
from zExceptions import Unauthorized
from five import grok
from zope import schema
from zope.component import adapts
from zope.component import getMultiAdapter
from zope.component import getUtility
from zope.event import notify
from zope.interface import Invalid
from zope.interface import Interface
from zope.schema import ValidationError
from z3c.form.interfaces import IValidator
from z3c.form.interfaces import IAddForm
from z3c.form.validator import SimpleFieldValidator
from plone.directives import dexterity
from plone.directives import form
from plone.uuid.interfaces import IUUID
from .. import MessageFactory as _
from Products.membrane.interfaces import user as membrane
from Products.CMFCore.interfaces import ISiteRoot
from Products.Archetypes.event import ObjectEditedEvent
from Products.statusmessages.interfaces import IStatusMessage
from plonetheme.nuplone.skin.interfaces import NuPloneSkin


RE_LOGIN = re.compile(r"^[a-z][a-z0-9-]+$")


class DuplicateLoginError(ValidationError):
    __doc__ = _("error_existing_login",
            default=u"This login name is already taken.")


def validLoginValue(value):
    if not RE_LOGIN.match(value):
        raise Invalid(_("error_invalid_login",
            default=u"A login name may only consist of lowercase letters "
                    u"and numbers."))
    return True


class LoginField(schema.TextLine):
    """A login name."""


class IUser(form.Schema):
    title = schema.TextLine(
            title=_("label_user_title", default=u"Name"),
            required=True)

    contact_email = schema.ASCIILine(
            title=_("label_contact_email", default=u"Contact email address"),
            required=True)

    login = LoginField(
            title=_("label_login_name", default=u"Login name"),
            required=True,
            constraint=validLoginValue)
    dexterity.write_permission(login="euphorie.ManageCountry")

    password = schema.Password(
            title=_("label_password", default=u"Password"),
            required=True)

    locked = schema.Bool(
            title=_("label_account_locked", default=u"Account is locked"),
            required=False,
            default=False)
    dexterity.write_permission(locked="euphorie.ManageCountry")


class UniqueLoginValidator(grok.MultiAdapter, SimpleFieldValidator):
    grok.implements(IValidator)
    grok.adapts(Interface, Interface, IAddForm, LoginField, Interface)

    def __init__(self, context, request, view, field, widget):
        self.context = context
        self.request = request
        self.view = view
        self.field = field
        self.widget = widget

    def validate(self, value):
        super(UniqueLoginValidator, self).validate(value)

        site = getUtility(ISiteRoot)
        for parent in aq_chain(site):
            if hasattr(aq_base(parent), "acl_users"):
                if parent.acl_users.searchUsers(login=value, exact_match=True):
                    raise DuplicateLoginError(value)


class UserProvider(object):
    """Base class for membrane adapters for :obj:`IUser` instances.

    This base class implements the
    :obj:`Products.membrane.interfaces.IMembraneUserObject` interface which is
    responisble for generating an id for a user object.

    This adapter does not claim to implement the `IMembraneUserObject`
    interface itself, since that would complicate the registration of the other
    adapters a little bit (`zope.component` can no longer determine the
    interface provided by an adapter if it provides multiple interfaces, even
    if they are derived classes).
    """
    adapts(IUser)

    def __init__(self, context):
        self.context = context

    def getUserId(self):
        uuid = IUUID(self.context, None)
        if uuid is None:
            # BBB for older instances
            return self.context.id
        return uuid

    def getUserName(self):
        return self.context.login


class UserAuthentication(grok.Adapter, UserProvider):
    """Account authentication routines.

    This adapter implements the
    :obj:`Products.membrane.interfaces.user.IMembraneUserAuth` interface. This
    interface is responsible for the authentication logic of accounts.
    """
    grok.context(IUser)
    grok.implements(membrane.IMembraneUserAuth)

    def authenticateCredentials(self, credentials):
        if self.context.locked:
            return None

        candidate = credentials.get("password", None)
        real = getattr(aq_base(self.context), "password", None)
        if candidate is None or real is None:
            return None

        if candidate == real:
            return (self.getUserId(), self.getUserName())

        return None


class UserChanger(grok.Adapter, UserProvider):
    """Account password changing.

    This adapter implements the
    :obj:`Products.membrane.interfaces.user.IMembraneUserChanger` interface.
    This interface is responsible for changing a users password.
    """
    grok.context(IUser)
    grok.implements(membrane.IMembraneUserChanger)

    def doChangeUser(self, userid, password, **kwargs):
        """Set the login name and password for a user.

        Changing the username is not allowed, and any attempt to do so will
        raise a `ValueError`.

        The *password* parameter is the plaintext password.
        """
        if userid != self.getUserId():
            raise ValueError("Userid changes are not allowed")
        self.context.password = password


class UserProperties(grok.Adapter, UserProvider):
    """User properties handling.

    This adapter implements the
    :obj:`Products.membrane.interfaces.user.IMembraneUserProperties` interface.
    This interface is responsible all handling of member properties.

    The interface is based on the basic PAS plugin
    :obj:`Products.PluggableAuthService.interfaces.IMutablePropertiesPlugin`
    interface. As a result all methods take a `user` parameter, which should
    always be the same as the adapted object for membrane adapters.
    """
    grok.context(IUser)
    grok.implements(membrane.IMembraneUserProperties)

    # A mapping for IUser properties to Plone user properties
    property_map = [("title", "fullname"),
                    ("contact_email", "email")]

    def getPropertiesForUser(self, user, request=None):
        properties = {}
        for (content_prop, user_prop) in self.property_map:
            value = getattr(self.context, content_prop)
            # None values are not allowed so replace those with an empty string
            properties[user_prop] = (value is not None) and value or u""
        return properties

    def setPropertiesForUser(self, user, propertysheet):
        marker = []
        changes = set()
        for (content_prop, user_prop) in self.property_map:
            value = propertysheet.getProperty(user_prop, default=marker)
            if value is not marker:
                setattr(self.context, content_prop, value)
                changes.add(content_prop)

        if changes:
            self.context.reindexObject(idxs=list(changes))
            notify(ObjectEditedEvent(self.context))


class Lock(grok.View):
    grok.context(IUser)
    grok.require("euphorie.content.ManageCountry")
    grok.layer(NuPloneSkin)
    grok.name("lock")

    def render(self):
        if self.request.method != "POST":
            raise Unauthorized
        authenticator = getMultiAdapter((self.context, self.request),
                name=u"authenticator")
        if not authenticator.verify():
            raise Unauthorized

        self.context.locked = locked = \
                (self.request.form.get("action", "lock") == "lock")
        flash = IStatusMessage(self.request).addStatusMessage
        if locked:
            flash(_("message_user_locked",
                    default=u'Account "${title}" has been locked.',
                    mapping=dict(title=self.context.title)), "success")
        else:
            flash(_("message_user_unlocked",
                    default=u'Account "${title}" has been unlocked.',
                    mapping=dict(title=self.context.title)), "success")

        country = aq_parent(aq_inner(self.context))
        self.request.response.redirect(
                "%s/@@manage-users" % country.absolute_url())
