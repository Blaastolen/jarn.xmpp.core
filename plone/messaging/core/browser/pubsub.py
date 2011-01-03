from z3c.form import form
from z3c.form import field
from z3c.form import button
from zope import schema
from zope.interface import Interface

from Products.CMFCore.utils import getToolByName

from plone.messaging.core import messageFactory as _
from plone.messaging.core.pubsub_utils import publishItemToNode


class IPublishToNode(Interface):

    node = schema.ASCIILine(title=_(u'Node'),
                          required=True)

    message = schema.Text(title=_(u'Message'),
                          required=True)


class PublishToNodeForm(form.Form):

    fields = field.Fields(IPublishToNode)
    label = _("Post message")
    ignoreContext = True

    def __init__(self, context, request, full=True):
        form.Form.__init__(self, context, request)
        self.all_fields = full

    def updateWidgets(self):
        """ Make sure that return URL is not visible to the user.
        """
        form.Form.updateWidgets(self)

        if not self.all_fields:
            # Hide fields which we don't want to bother user with
            self.widgets["node"].mode = form.interfaces.HIDDEN_MODE

    @button.buttonAndHandler(_('Post'), name='publish_message')
    def publish(self, action):
        data, errors = self.extractData()
        if errors:
            return
        node = data['node']
        message = data['message']
        transforms = getToolByName(self.context, 'portal_transforms')
        message = transforms.convert('web_intelligent_plain_text_to_html',
                                     message).getData()
        pm = getToolByName(self.context, 'portal_membership')
        user = pm.getAuthenticatedMember().getUserId()
        publishItemToNode(node, message, user)
        return self.request.response.redirect(self.context.absolute_url())