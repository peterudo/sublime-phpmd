# -- coding: utf-8 --

import sublime
import sublime_plugin
import subprocess
import threading
import re
from xml.dom.minidom import parseString


region_key = "PHPMD"

settings = sublime.load_settings('phpmd.sublime-settings')
phpmd_exec = settings.get("phpmd_executable")
phpmd_options = settings.get("phpmd_options")
phpmd_output_format = settings.get("phpmd_output_format")


def is_php(view):
    return re.search('.+\PHP.tmLanguage', view.settings().get('syntax'))


class PhpmdCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        ''' Runs the phpmd command for the current view'''

        if not is_php(self.view):
            return None

        thread = PhpmdThread(self.view.file_name())
        thread.start()

        self.handle_thread(thread)

    def handle_thread(self, thread):
        '''Handle the running thread. Will rerun itself until the thread has completed/failed'''

        if thread.is_alive():
            sublime.set_timeout(lambda: self.handle_thread(thread), 100)
            return

        if thread.result == False:
            return

        self.parse_data(thread.result)

    def parse_data(self, data):
        '''Parse the result from the thread and mark the regions containing errors'''

        regions = []
        xml_data = parseString(data)
        violations = xml_data.getElementsByTagName('violation')

        for violation in violations:
            attr = violation.getAttribute
            beginline = attr('beginline')
            endline = attr('endline')

            message = phpmd_output_format.format(\
                beginline=beginline,\
                endline=endline,\
                rule=attr('rule'),\
                message=violation.firstChild.nodeValue.strip()\
            )

            print message

            for lineno in xrange(int(beginline), int(endline) + 1):
                line = self.view.full_line(self.view.text_point(lineno - 1, 0))

                region = sublime.Region(line.begin(), line.end())
                regions.append(region)

        self.view.erase_regions(region_key)
        self.view.add_regions(region_key, regions, \
            "punctuation.section.embedded.begin", \
            "light_x_bright", sublime.HIDDEN)


class PhpmdThread(threading.Thread):

    def __init__(self, file_name):
        self.file_name = file_name
        self.result = None

        threading.Thread.__init__(self)

    def run(self):
        '''Run the phpmd utility and store the result'''

        cmd = "%s %s xml %s" \
            % (phpmd_exec, self.file_name, phpmd_options)

        proc = subprocess.Popen([cmd], \
            shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        if proc.stdout:
            self.result = proc.communicate()[0]
            return


class PhpmdEventListener(sublime_plugin.EventListener):

    def on_load(self, view):
        view.run_command('phpmd')

    def on_post_save(self, view):
        view.run_command('phpmd')
