import sublime, sublime_plugin
import os
import re
import json

settings = sublime.load_settings("CheatSheet.sublime-settings")


def prettifySnake(string):
    return string.replace('_', ' ').title()


def dictString(dictionary):
    if isinstance(dictionary, dict):
        string = []
        for key, value in dictionary.iteritems():
            string.append(key + ': ' + dictString(value))
        return u'{' + u', '.join(string) + u'}'
    elif isinstance(dictionary, list):
        return u'[' + u', '.join(map(lambda x: dictString(x), dictionary)) + u']'
    else:
        return unicode(dictionary).replace('\t', u'\u21e5')


OPERATORS = {
    'equal': '=',
    'not_equal': u'\u2260',
    'regex_match': 'matches',
    'regex_contains': 'contains'
}


def stringify_context(context):
    key = context.get('key') or ''
    operator = context.get('operator')
    operator = OPERATORS.get(operator)
    operand = context.get('operand')
    string = u'{key} {operator} {operand}'
    if key.startswith('setting.'):
        if operand is True:
            key = key.replace('setting.', u'\u2611')
            string = u'{key}'
        elif operand is False:
            key = key.replace('setting.', u'\u2612')
            string = u'{key}'
        else:
            key = key.replace('setting.', u'\u2699')
    if (operator == '=' and operand is True) or (operator is None and operand is None):
        string = u'{key}'
    elif operator is None:
        string = u'{key} = {operand}'
    elif key == 'preceding_text' and (operator == 'contains' or operator == 'matches') and operand.endswith('$'):
        string = u'preceded by {operand}'
    elif key == 'following_text' and (operator == 'contains' or operator == 'matches') and operand.startswith('^'):
        string = u'followed by {operand}'
    else:
        operand = str(operand).replace('\t', '\\t').replace('\n', '\\n')
    return string.format(key=key, operator=operator, operand=operand)


def formatUnknownName(name, args):
    string = prettifySnake(name)
    if args is not None and len(args) > 0:
        string += ' - ' + dictString(args)
    return string


def getCommandDisplayName(name, args):
    # special case for set_layout
    if name == 'set_layout':
        cols = len(args['cols']) - 1
        rows = len(args['rows']) - 1
        description = '{cols} x {rows}'
        if rows == 1 and cols == 1:
            description = 'Single'
        elif rows == 1:
            description = '{cols} columns'
        elif cols == 1:
            description = '{rows} rows'
        return 'Set Layout - ' + description.format(rows=rows, cols=cols)
    # normal case
    if name in COMMANDS:
        if isinstance(COMMANDS[name], str):
            return COMMANDS[name]
        else:
            displayName = getValueInDict(COMMANDS[name], args)
            return displayName or formatUnknownName(name, args)
    else:
        return formatUnknownName(name, args)


def getValueInDict(dictionary, args):
    if args is None:
        return None
    for key, value in args.iteritems():
        if key not in dictionary:
            continue
        if isinstance(dictionary[key], str):
            value = str(value)
            filename = os.path.splitext(os.path.basename(value))[0]
            return dictionary[key].format(value=value, pvalue=prettifySnake(value), filename=filename)
        elif value in dictionary[key]:
            if isinstance(dictionary[key][value], str):
                return dictionary[key][value]
            else:
                return getValueInDict(dictionary[key][value], args)
        elif '@default' in dictionary[key] and isinstance(dictionary[key]['@default'], str):
            value = str(value)
            filename = os.path.splitext(os.path.basename(value))[0]
            return dictionary[key]['@default'].format(value=value, pvalue=prettifySnake(value), filename=filename)
    if '@default' in dictionary:
        return getValueInDict(dictionary['@default'], args)


KEYCHARS = {
    'super': u'\u2318',
    'alt': u'\u2325',
    'shift': u'\u21e7',
    'ctrl': u'\u2303',
    'up': u'\u2191',
    'down': u'\u2193',
    'left': u'\u2190',
    'right': u'\u2192',
    'escape': u'\u238b',
    'tab': u'\u21e5',
    'space': 'Space',
    'enter': u'\u21a9',
    'backspace': u'\u232b',
    'delete': u'\u2326',
    'forward_slash': '\\',
    'plus': '+',
    'equals': '=',
    'minus': '-',
    'backquote': '`'
}


def prettifyKeys(keylist):
    pretty = []
    for keystr in keylist:
        keys = keystr.split('+')
        keystring = ''
        for key in keys:
            keystring += KEYCHARS.get(key) or key.upper()
        pretty.append(keystring)
    return '  '.join(pretty)


COMMANDS = {
    'show_overlay': {
        'overlay': {
            'goto': {
                'text': {
                    '@': 'Goto Symbol',
                    ':': 'Goto Line',
                    '#': 'Seach Keywords'
                },
                'show_files': {
                    True: 'Goto Anything'
                }
            },
            'command_palette': 'Command Palette'
        }
    },
    'show_panel': {
        'panel': {
            'console': 'Show Console',
            'find_in_files': 'Find in Files',
            'output.exec': 'Show Build Results',
            'find': 'Find...',
            'replace': 'Find and Replace',
            'incremental_find': {
                'reverse': {
                    True: 'Incremental Find (reverse)',
                    False: 'incremental Find'
                }
            }
        }
    },
    'run_zen_action': {
        'action': 'Zen Action: {pvalue}'
    },
    'insert_snippet': {
        'contents': 'Insert Snippet: {value}',
        'name': 'Insert Snippet: {value}'
    },
    'run_macro_file': {
        'file': 'Run Macro File: {filename}'
    },
    'expand_selection': {
        'to': 'Expand Selection to {value}'
    },
    'open_file': {
        'file': {
            '${packages}/User/Preferences.sublime-settings': 'User Preferences'
        }
    },
    'switch_file': {
        'extensions': 'Switch header / implementation file'
    },
    'move_to': {
        'to': 'Move to {value}'
    },
    'move_to_group': {
        'group': 'Move to Group {value}'
    },
    'select_by_index': {
        'index': 'Select by Index {value}'
    },
    'fold_by_level': {
        'level': {
            1: 'Fold all',
            '@default': 'Fold level {value}'
        }
    },
    'focus_group': {
        'group': 'Focus group {value}'
    },
    'toggle_comment': {
        'block': {
            True: 'Toggle Block Comment',
            False: 'Toggle Line Comment'
        }
    },
    'select_lines': {
        'forward': {
            True: 'Select Line Below',
            False: 'Select Line Above'
        }
    },
    'scroll_lines': {
        'amount': {
            1.0: 'Scroll Up 1 Line',
            -1.0: 'Scroll Down 1 Line',
            '@default': 'Scroll {value} Lines'
        }
    },
    'move': {
        'extend': {
            True: {
                'forward': {
                    True: {
                        'by': 'Expand Selection by {pvalue}'
                    },
                    False: {
                        'by': 'Expand Selection Backwards by {pvalue}'
                    }
                }
            }
        },
        '@default': {
           'forward': {
                True: {
                    'by': 'Move Forward by {pvalue}'
                },
                False: {
                    'by': 'Move Backwards by {pvalue}'
                }
            }
        }
    }
}


class CheatSheetCommand(sublime_plugin.TextCommand):
    """
    Cheat sheet for keyboard shortcuts
    """
    #add some default very usefull commands;
    defaultCommand = []
    #installed plugins list
    plugins = None

    plugins_keys = None

    def run(self, edit):
        self.defaultCommand.sort(key=lambda x: x["name"].lower())

        if self.plugins == None:
            self.plugins = []
        if self.plugins_keys == None:
            self.plugins_keys = {}
        path = sublime.packages_path()
        dirs = os.listdir(path)
        #sort with insensitive
        dirs.sort(key=lambda x: x.lower())
        plugins = []
        global_ignored = sublime.load_settings('Global.sublime-settings').get('ignored_packages')
        ignored_packages = set(settings.get("ignored_packages") + global_ignored)
        single_max_nums = int(settings.get("single_max_nums") or -1)
        for name in dirs:
            if name in ignored_packages:
                continue
            dir = path + '/' + name + '/'
            if not os.path.isdir(dir):
                continue
            platform = sublime.platform().lower().title()
            keymapFile = dir + "Default (" + platform + ").sublime-keymap"
            if not os.path.isfile(keymapFile):
                keymapFile = dir + "Default.sublime-keymap"
            if not os.path.isfile(keymapFile):
                continue
            #plugins.append(keymapFile)
            with open(keymapFile) as f:
                content = f.read()
                # remove comments since python JSON does not handle them
                blockcomment = re.compile('/\*.*?\*/', re.DOTALL | re.MULTILINE)
                content = re.sub(blockcomment, '', content)
                content = re.sub('//.*?\n', '', content)
                try:
                    jsonData = json.loads(content)
                except ValueError as e:
                    print str(e)
                    continue

            if not isinstance(jsonData, list):
                continue
            i = 0
            for item in jsonData:
                if "keys" not in item or "command" not in item:
                    continue
                if single_max_nums <= 0 or i <= single_max_nums:
                    keys = item["keys"]
                    if not isinstance(keys, list):
                        keys = [keys]

                    if settings.get('ignore_single_key') and len(keys) == 1 and '+' not in keys[0]:
                        continue
                    keys = prettifyKeys(keys)
                    command = item["command"]
                    item['name'] = name
                    cmd = item.get('description') or getCommandDisplayName(command, item.get('args'))
                    title = u'{keys} - {name}'.format(name=name, keys=keys)
                    # show all the context
                    if settings.get('show_context') and 'context' in item:
                        title += u' {context}'.format(context=dictString(map(stringify_context, item['context'])))
                    # show the selector (syntax or scope)
                    if 'context' in item: 
                        for context in item['context']:
                            if context.get('key') == 'selector':
                                title += u' <{selector}>'.format(selector=context['operand'])
                    plugins.append([cmd, title])
                    self.plugins.append(item)
                    i += 1

        for item in self.defaultCommand:
            plugins.append([item['name'], item['command'] + " : " + ",".join(item['keys'])])
            self.plugins.append(item)

        self.view.window().show_quick_panel(plugins, self.panel_done)

    #panel done
    def panel_done(self, picked):
        if picked == -1:
            return
        item = self.plugins[picked]
        if self.checkContext(item) == False:
            return
        args = {}
        if "args" in item:
            args = item['args']
        #thanks wuliang
        self.view.run_command(item['command'], args)
        self.view.window().run_command(item['command'], args)
        sublime.run_command(item['command'], args)

    #check context condition
    def checkContext(self, plugin):
        return True
        if 'context' not in plugin:
            return True
        if 'window' in plugin and plugin['window']:
            return True
        # context = plugin["context"]
        # name = plugin["name"]
        # path = path = sublime.packages_path() + '/' + name + '/'
        import glob
        pyFiles = glob.glob('*.py')
        sublime.status_message(",".join(pyFiles))
        return True
