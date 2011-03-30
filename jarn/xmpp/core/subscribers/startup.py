import logging

from twisted.internet import defer
from zope.component import getGlobalSiteManager
from zope.component import getUtility
from zope.component import queryUtility


from jarn.xmpp.core.client import AdminClient
from jarn.xmpp.core.interfaces import IAdminClient
from jarn.xmpp.core.interfaces import IPubSubStorage

logger = logging.getLogger('jarn.xmpp.core')


def setupAdminClient(portal, event):
    if queryUtility(IAdminClient) is None:
        gsm = getGlobalSiteManager()
        try:
            client = AdminClient()
            gsm.registerUtility(client, IAdminClient)
        except:
            logger.error('Could not load AdminClient')


def adminConnected(event):
    client = event.object
    # Since this is our initial connection, populate ram storage with the
    # pubsub nodes.
    populatePubSubStorage()
    client.admin.sendAnnouncement("Instance started")

    # Register user subscribers
    import user_management
    gsm = getGlobalSiteManager()
    gsm.registerHandler(user_management.onUserCreation)
    gsm.registerHandler(user_management.onUserDeletion)


def populatePubSubStorage():
    """ XXX TODO:
    1) I retrieve every node and items. Change this to retrieve only those
    where the admin is subscribed. The rest are not used.
    2) This would have been simpler if ejabberd supported retrieving
    collection items as it should. Argue in the mailing list.
    """

    client = getUtility(IAdminClient)
    storage = getUtility(IPubSubStorage)

    def getChildNodes(parent):

        def gotNodeItems(result):
            node, items = result
            storage.node_items[node] = items
            if parent:
                storage.node_items[parent] = \
                    storage.node_items[parent] + (items)
                storage.node_items[parent].sort(
                    key=lambda item: item['updated'],
                    reverse=True)

        def gotNodeAffiliations(result):
            node, affiliations = result
            publishers = [jid.user
                          for jid, role in affiliations
                          if role=='publisher']
            storage.publishers[node] = publishers

        def gotNodeTypes(result):
            cNodes = []
            lNodes = []
            for success, res in result:
                if success:
                    node, node_type = res
                    if node_type == 'collection':
                        cNodes.append(node)
                    else:
                        lNodes.append(node)

            deferred_list = []
            for node in cNodes:
                storage.collections[node] = []
                storage.node_items[node] = []
                if parent:
                    storage.collections[parent].append(node)
                deferred_list.append(getChildNodes(node))

            for node in lNodes:
                storage.leaf_nodes.append(node)
                if parent:
                    storage.collections[parent].append(node)
                d = client.getNodeItems(node)
                d.addCallback(gotNodeItems)
                deferred_list.append(d)
                d = client.getNodeAffiliations(node)
                d.addCallback(gotNodeAffiliations)
                deferred_list.append(d)

            return defer.DeferredList(deferred_list)

        def gotNodes(result):
            d = defer.DeferredList(
                [client.getNodeType(node_dict['node'])
                 for node_dict in result],
                consumeErrors=True)
            d.addCallback(gotNodeTypes)
            return d

        d = client.getNodes(parent)
        d.addCallback(gotNodes)
        return d

    d = getChildNodes(None)
    return d
