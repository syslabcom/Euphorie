import re
from AccessControl import ClassSecurityInfo
from App.class_init import InitializeClass
from Products.PlonePAS.plugins import passwordpolicy
from Products.PluggableAuthService.interfaces.plugins import IValidationPlugin
from euphorie.content import MessageFactory as _
from zope.interface import implements


class EuphoriePasswordPolicy(passwordpolicy.PasswordPolicyPlugin):
    """Simple Password Policy to ensure password is 5 chars long.
    """
    id = "euphorie_password_policy"
    meta_type = "Euphorie Password Policy"
    implements(IValidationPlugin)
    security = ClassSecurityInfo()

    security.declarePrivate('validateUserInfo')
    def validateUserInfo(self, user, set_id, set_info ):
        """ See IValidationPlugin. Used to validate password property
        """
        if not set_info:
            return []
        password = set_info.get('password', None)
        if password is None:
            return []

        failed = False
        if len(password) < 5:
            failed = True
        elif len([l for l in password if l.isupper()]) == 0:
            # Must have capital letter(s)
            failed = True
        elif not re.match("[1-9]"):
            # Must have numbers(s)
            failed = True
        elif not re.match("[^a-zA-Z1-9"):
            # Must have special chars (i.e. not alphanumerical)
            failed = True

        if failed:
            return [{'id':'password','error': _(
                u"Your password must contain at least 5 characters, "
                u"including at least one capital letter, one number and "
                u"one special character (e.g. $, # or @')."
            )}]
        else:
            return []

InitializeClass(EuphoriePasswordPolicy)

