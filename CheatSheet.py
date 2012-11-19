import sublime, sublime_plugin
import os
import re
import json

settings = sublime.load_settings("KeymapManager.sublime-settings")


def prettifySnake(string):
    return string.replace('_', ' ').title()


def dictString(dictionary):
    if isinstance(dictionary, dict):
        string = []
        for key, value in dictionary.iteritems():
            string.append(key + ': ' + dictString(value))
        return '{' + ', '.join(string) + '}'
    elif isinstance(dictionary, list):
        return '[' + ', '.join(map(lambda x: dictString(x), dictionary)) + ']'
    else:
        return str(dictionary)


def formatUnknownName(name, args):
    string = prettifySnake(name)
    if args is not None:
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
            filenameext = os.path.basename(value)
            filename = os.path.splitext(filenameext)[0]
            return dictionary[key].format(value=value, pvalue=prettifySnake(value), filename=filename, filenameext=filenameext)
        elif value in dictionary[key]:
            if isinstance(dictionary[key][value], str):
                return dictionary[key][value]
            else:
                return getValueInDict(dictionary[key][value], args)


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
                    for key in keys:
                        if key not in self.plugins_keys:
                            self.plugins_keys[key] = []
                        if item["command"] not in self.plugins_keys[key]:
                            self.plugins_keys[key].append(item["command"])

                    if isinstance(keys, list):
                        keys = prettifyKeys(keys)
                    command = item["command"]
                    item["name"] = name
                    cmd = item.get('description') or getCommandDisplayName(command, item.get('args'))
                    title = u'{0} - {1}'.format(name, keys)
                    plugins.append([cmd, title])
                    self.plugins.append(item)
                    i += 1

        for item in self.defaultCommand:
            plugins.append([item['name'], item['command'] + " : " + ",".join(item['keys'])])
            self.plugins.append(item)

        plugins.append(["KeymapConflict", "check plugins keymap conflict"])
        self.plugins.append({"name": "KeymapConflict"})

        self.view.window().show_quick_panel(plugins, self.panel_done)

    #panel done
    def panel_done(self, picked):
        if picked == -1:
            return
        item = self.plugins[picked]
        if item["name"] == "KeymapConflict":
            self.checkKeymapConflict()
            return
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
        if "context" not in plugin:
            return True
        if "window" in plugin and plugin["window"]:
            return True
        # context = plugin["context"]
        # name = plugin["name"]
        # path = path = sublime.packages_path() + '/' + name + '/'
        import glob
        pyFiles = glob.glob("*.py")
        sublime.status_message(",".join(pyFiles))
        return True

    def checkKeymapConflict(self):
        keymapConflict = []
        for key, item in self.plugins_keys.items():
            if len(item) > 1:
                keymapConflict.append([key, "Conflict in \"" + ", ".join(item) + "\" commands"])
        if len(keymapConflict) > 0:
            self.view.window().show_quick_panel(keymapConflict, self.check_panel_done)

    def check_panel_done(self, picked):
        pass
