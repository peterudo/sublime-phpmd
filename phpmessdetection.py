# -- coding: utf-8 --

import sublime
import sublime_plugin
import subprocess
import threading
from xml.dom.minidom import parseString


settings = sublime.load_settings('Base File.sublime-settings')
region_key = "PHPMD"
phpmd_exec = settings.get("phpmd_executable", "/opt/local/bin/phpmd")


class PHPMDListener(sublime_plugin.EventListener):

    def on_post_save(self, view):
        self.view = view

        thread = PHPMessDetector(self.view.file_name())
        thread.start()

        self.handle_thread(thread)

    def handle_thread(self, thread):
        if thread.is_alive():
            sublime.set_timeout(lambda: self.handle_thread(thread), 100)
            return

        if thread.result == False:
            return

        self.parse_data(thread.result)

    def parse_data(self, data):
        regions = []
        xml_data = parseString(data)
        violations = xml_data.getElementsByTagName('violation')

        for violation in violations:
            beginline = violation.getAttribute('beginline')
            endline = violation.getAttribute('endline')

            for lineno in xrange(int(beginline), int(endline) + 1):
                line = self.view.full_line(self.view.text_point(lineno - 1, 0))

                region = sublime.Region(line.begin(), line.end())
                regions.append(region)

        self.view.erase_regions(region_key)
        self.view.add_regions(region_key, regions, \
            "punctuation.section.embedded.begin", \
            "light_x_bright", sublime.HIDDEN)


class PHPMessDetector(threading.Thread):

    def __init__(self, file):
        self.file = file
        self.result = None

        threading.Thread.__init__(self)

    def run(self):
        cmd = "%s %s xml codesize,unusedcode,naming,design" \
            % (phpmd_exec, self.file)

        proc = subprocess.Popen([cmd], \
            shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        if proc.stdout:
            self.result = proc.communicate()[0]
            return
