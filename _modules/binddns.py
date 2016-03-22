
def node_replace(node, minion_id_replace):
    for key, repl in minion_id_replace.iteritems():
        node = node.replace(repl.from, repl.to)
    return node
