from euphorie.deployment.tests.functional import EuphorieTestCase
from euphorie.deployment.tests.functional import EuphorieFunctionalTestCase


class RiskTests(EuphorieTestCase):
    def _create(self, container, *args, **kwargs):
        newid=container.invokeFactory(*args, **kwargs)
        return getattr(container, newid)

    def createRisk(self):
        country=self.portal.sectors.nl
        sector=self._create(country, "euphorie.sector", "sector")
        surveygroup=self._create(sector, "euphorie.surveygroup", "group")
        survey=self._create(surveygroup, "euphorie.survey", "survey")
        module=self._create(survey, "euphorie.module", "module")
        risk=self._create(module, "euphorie.risk", "risk")
        return risk

    def testNotGloballyAllowed(self):
        self.loginAsPortalOwner()
        types=[fti.id for fti in self.portal.allowedContentTypes()]
        self.failUnless("euphorie.risk" not in types)

    def testAllowedContentTypes(self):
        self.loginAsPortalOwner()
        risk=self.createRisk()
        types=[fti.id for fti in risk.allowedContentTypes()]
        self.assertEqual(set(types), set(["euphorie.solution"]))

    def testCanBeCopied(self):
        self.loginAsPortalOwner()
        risk=self.createRisk()
        self.assertTrue(risk.cb_isCopyable())



class RiskFunctionalTests(EuphorieFunctionalTestCase):
    def _create(self, container, *args, **kwargs):
        newid=container.invokeFactory(*args, **kwargs)
        return getattr(container, newid)

    def createRisk(self):
        country=self.portal.sectors.nl
        sector=self._create(country, "euphorie.sector", "sector")
        surveygroup=self._create(sector, "euphorie.surveygroup", "group")
        survey=self._create(surveygroup, "euphorie.survey", "survey")
        module=self._create(survey, "euphorie.module", "module")
        risk=self._create(module, "euphorie.risk", "risk")
        return risk

    def adminBrowser(self):
        from Products.PloneTestCase.setup import portal_owner
        from Products.PloneTestCase.setup import default_password
        from Products.Five.testbrowser import Browser
        browser=Browser()
        browser.open("%s/@@login" % self.portal.absolute_url())
        browser.getControl(name="__ac_name").value=portal_owner
        browser.getControl(name="__ac_password").value=default_password
        browser.getForm(id="loginForm").submit()
        return browser

    def testDescriptionSanitised(self):
        self.loginAsPortalOwner()
        risk=self.createRisk()
        risk.title=u"Risk title"
        risk.problem_description=u"Problem description"
        browser=self.adminBrowser()
        browser.open("%s/@@edit" % risk.absolute_url())
        browser.getControl(name="form.widgets.description").value=u"Raw text"
        browser.getControl(name="form.buttons.save").click()
        self.assertEqual(risk.description, u"<p>Raw text</p>")

    def testLegalReferenceSanitised(self):
        self.loginAsPortalOwner()
        risk=self.createRisk()
        risk.title=u"Risk title"
        risk.description=u"<p>Description</p>"
        risk.problem_description=u"Problem description"
        browser=self.adminBrowser()
        browser.open("%s/@@edit" % risk.absolute_url())
        browser.getControl(name="form.widgets.legal_reference").value=u"Raw text"
        browser.getControl(name="form.buttons.save").click()
        self.assertEqual(risk.legal_reference, u"<p>Raw text</p>")

    def testImageFromOtherSectorAccount(self):
        # http://code.simplon.biz/tracker/euphorie/ticket/143
        import re
        from euphorie.content.tests.utils import createSector
        from euphorie.content.tests.utils import addSurvey
        from Products.Five.testbrowser import Browser
        sector=createSector(self.portal, login="sector")
        self.loginAsPortalOwner()
        survey=addSurvey(sector)
        createSector(self.portal, id="sector2", login="sector2", password="sector2")
        self.logout()
        browser=Browser()
        browser.open("%s/@@login" % self.portal.absolute_url())
        browser.getControl(name="__ac_name").value="sector2"
        browser.getControl(name="__ac_password").value="sector2"
        browser.getForm(id="loginForm").submit()
        risk=survey["1"]["2"]
        browser.open(risk.absolute_url())
        match=re.search(r'<div class="introduction">\s*<img[^>]+src="([^"]+)', browser.contents)
        self.assertTrue(match)
        image_url=match.group(1)
        browser.open(image_url)
        self.assertEqual(browser.isHtml, False)
        self.assertEqual(browser.headers.maintype, "image")



class ConstructionFilterTests(EuphorieTestCase):
    def _create(self, container, *args, **kwargs):
        newid=container.invokeFactory(*args, **kwargs)
        return getattr(container, newid)

    def createStructure(self):
        self.country=self.portal.sectors.nl
        self.sector=self._create(self.country, "euphorie.sector", "sector")
        self.surveygroup=self._create(self.sector, "euphorie.surveygroup", "group")
        self.survey=self._create(self.surveygroup, "euphorie.survey", "survey")
        self.module=self._create(self.survey, "euphorie.module", "module")

    def testPreventRiskIfModuleExists(self):
        self.setRoles(["Manager"])
        self.createStructure()
        types=[fti.id for fti in self.module.allowedContentTypes()]
        self.failUnless("euphorie.risk" in types)
        self._create(self.module, "euphorie.module", "module")
        types=[fti.id for fti in self.module.allowedContentTypes()]
        self.failUnless("euphorie.risk" not in types)

