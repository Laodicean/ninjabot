# Regex Plugin for ninjabot

from collections import defaultdict, deque
import re

BACKLOG = 3 # keep this many past messages saved for each user

last_messages = defaultdict(deque)

class Plugin:
    def __init__(self, controller, config):
        self.controller = controller

    def on_incoming(self, msg):
        # Ignore those who have been ignored...
        if self.controller.is_ignored(msg.nick):return

        if msg.type == msg.CHANNEL:
            # check if the message matches the s/blah/blah/ syntax
            # regex could have been used for this, but factoring in those escaped forward slashes
            # would have been more trouble than it was worth...
            body = msg.body
            their_messages = last_messages[msg.nick]

            groups = list()
            current_group = ''
            for i in xrange(len(body)):
                if i == 0 and body[i] != 's':
                    break
                elif i == 1 and body[i] != '/':
                    break
                elif body[i] == '/' and (body[i-1] != '\\' or (len(body) >= 3 and body[i-2] == '\\')):
                    groups.append(current_group)
                    current_group = ''
                else:
                    current_group += body[i]
            else:
                # take pity on the user if they haven't finished the expression with a forward slash
                if len(groups) == 2 and len(current_group) > 0:
                    groups.append(current_group)
                    current_group = ''

                flags = current_group

                if (flags == 'g' or flags.isdigit() or len(flags) == 0) and len(groups) == 3:
                    # did they have a last message?
                    if msg.nick in last_messages:
                        _, pattern, replacement = map(lambda s: s.replace('\\/', '/'), groups)
                        # escape backslashes
                        replacement = replacement.replace('\\', '\\\\')

                        # scan for a matching message in their last messages
                        for message in their_messages:
                            try: # will treat the regex as a normal message if an error occurs, i.e. invalid syntax
                                if re.search(pattern, message):
                                    if 'g' in flags:
                                        body = re.sub(pattern, replacement, message)
                                    elif flags.isdigit():
                                        matches = [m for m in re.finditer(pattern, message)]
                                        if len(matches) >= int(flags):
                                            span = matches[int(flags)-1].span()
                                            body = message[:span[0]] + replacement + message[span[1]:]
                                            print body
                                        else:
                                            return
                                    else:
                                        body = re.sub(pattern, replacement, message, 1)
                                        
                                    # put backslashes back in
                                    body = body.replace('\\\\', '\\')

                                    # send it
                                    if body == "":
                                        self.controller.privmsg(msg.channel, '%s said nothing' % msg.nick)
                                    else:
                                        self.controller.privmsg(msg.channel, '%s meant to say: %s' % (msg.nick, body))

                                    break
                            except:
                                pass
                        else:
                            # match wasn't found
                            # return without adding this to their last messages
                            return

            # add it to the last messages dictionary
            their_messages = last_messages[msg.nick]
            their_messages.appendleft(body)
            if len(their_messages) > BACKLOG:
                their_messages.pop()
