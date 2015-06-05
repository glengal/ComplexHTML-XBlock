"""
ComplexHTML XBlock for edX
Author: Raymond Lucian Blaga
Description: An HTML, JavaScript and CSS Editing XBlock that records student interactions if the course author wishes it.
"""

import urllib, datetime, json
from .utils import render_template, load_resource, resource_string
from django.template import Context, Template
from xblock.core import XBlock
from xblock.fields import Scope, Integer, List, String
from xblock.fragment import Fragment

class ComplexHTMLXBlock(XBlock):

    display_name = String(
        display_name="Complex HTML XBlock",
        help="This name appears in the horizontal navigation at the top of the page",
        scope=Scope.settings,
        default="Complex HTML XBlock"
    )

    body_html = String(
        help="HTML code of the block",
        default="<p>Body of the block goes here...</p>", scope=Scope.content
    )

    body_tracked = String(
        help="List of tracked elements",
        default="p", scope=Scope.content
    )

    body_js = String(
        help="JavaScript code for the block",
        default="console.log(\"Hello world.\");", scope=Scope.content
    )

    body_json = String(
        help="JSON container that can be used by the JavaScript code above",
        default="{\"sample\": { \"subsample\": \"true\" }}", scope=Scope.content
    )

    body_css = String(
        help="CSS code for the block",
        default="p { color: red }", scope=Scope.content
    )

    settings_student = String(
        help="Student-specific settings for student view in JSON form; initially a copy of body_json",
        default="", scope=Scope.user_state
    )

    grabbed = List(
        help="Student interaction that was grabbed from XBlock.",
        default=[], scope=Scope.user_state
    )

    @XBlock.json_handler
    def get_body_html(self, data, suffix=''):
        return {"body_html": self.body_html}

    @XBlock.json_handler
    def get_body_css(self, data, suffix=''):
        return {"body_css": self.body_css}

    @XBlock.json_handler
    def get_body_js(self, data, suffix=''):
        return {"body_js": self.body_js}

    @XBlock.json_handler
    def get_body_json(self, data, suffix=''):
        return {"body_json": self.body_json}

    @XBlock.json_handler
    def get_settings_student(self, data, suffix=''):
        return {"json_settings": self.settings_student}

    @XBlock.json_handler
    def get_grabbed_data(self, data, suffix=''):
        return {"grabbed_data": self.grabbed}

    def get_time_delta(self):
        """
        Return time difference between current grabbed input and the previous one.
        """
        return self.grabbed[-1] - self.grabbed[-2]

    @XBlock.json_handler
    def grab_data(self, data, suffix=''):
        """
        Grab data from recordable fields and append it to self.grabbed.
        """

        content = {"time": str(datetime.datetime.now())}
        chunk = []

        for i in data:
            chunk.append((str(i), str(data[i])))

        if len(chunk) > 0:
            self.grabbed.append((content["time"], chunk))
            content["data"] = chunk

        else:
            self.grabbed.append((content["time"], "crickets"))
            content["data"] = None

        print "Grabbed data on " + self.grabbed[-1][0]
        for i in self.grabbed[-1][1]:
            print "+--" + str(i)

        return content

    @XBlock.json_handler
    def clear_data(self, data, suffix=''):
        """
        Clear data grabbed from student
        """
        self.grabbed = []
        return {"cleared": "yes"}

    @XBlock.json_handler
    def update_student_settings(self, data, suffix=''):
        """
        Update student settings from AJAX request
        """
        if self.settings_student != data["json_settings"]:
            self.settings_student = data["json_settings"]
            return {"updated": "true"}
        return {"updated": "false"}

    @staticmethod
    def generate_css(css, block):
        """
        Generate CSS text for block
        """
        # assuming course author places the opening accolade on the same line as the selectors
        # ie the first line for each CSS element should be as follows ".this_is_a_selector {"

        result = ""

        for i in css.split('\n'):
            if i.find('{') != -1:
                result += block + " " + i
            else:
                result += i
            result += '\n'

        return result

    @XBlock.json_handler
    def get_generated_css(self, data, suffix=''):
        """
        Generate CSS text fo block and return it via AJAX request
        """
        content = {"css": ""}
        if self.body_css != "" and data["block"] != "":
            content["css"] = self.generate_css(data["css"], data["block"])
            return content
        return content

    def student_view(self, context=None):
        """
        The student view
        """

        fragment = Fragment()
        content = {'self': self}
        
        if self.settings_student == "":
            self.settings_student = self.body_json

        # Build page based on user input HTML, JS and CSS code
        # basic check for url
        if self.body_html[:4] == "http":
            body_html = "<div class=\"complexhtml_xblock\">" + urllib.urlopen(self.body_html).read() + "</div>"
        else:
            body_html = "<div class=\"complexhtml_xblock\">" + self.body_html + "</div>"

        # Build slide specific JavaScript code
        body_js = load_resource('static/js/complexhtml.js')
        tracked = ""

        # Generate AJAX request for each element that will be tracked
        for i in self.body_tracked.split("\n"):
            e = i.split(", ")
            tracked += "recordClick(\'" + e[0] + "\'"
            if len(e) > 1:
                tracked += ", \'" + e[1] + "\'"
            tracked += ");\n"

        body_js = body_js[:-47] + tracked + body_js[-47:]

        # basic check for url
        if self.body_js[:4] == "http":
            body_js = body_js[:-7] + urllib.urlopen(self.body_js).read() + body_js[-7:]
        else:
            body_js = body_js[:-7] + self.body_js + body_js[-7:]

        # basic check for url
        if self.body_css[:4] == "http":
            body_css_tmp = urllib.urlopen(self.body_css).read()
        else:
            body_css_tmp = self.body_css

        body_css = self.generate_css(body_css_tmp, ".complexhtml_xblock")

        fragment.add_content(Template(unicode(body_html)).render(Context(content)))
        fragment.add_javascript(unicode(body_js))
        fragment.add_css(unicode(body_css))
        fragment.add_content(render_template('templates/complexhtml.html', content))
        fragment.add_css(load_resource('static/css/complexhtml.css'))
        fragment.initialize_js('ComplexHTMLXBlock')

        return fragment

    def studio_view(self, context=None):
        """
        The studio view
        """

        fragment = Fragment()

        # Load CodeMirror
        fragment.add_javascript(load_resource('static/js/codemirror/lib/codemirror.js'))
        fragment.add_javascript(load_resource('static/js/codemirror/mode/xml/xml.js'))
        fragment.add_javascript(load_resource('static/js/codemirror/mode/htmlmixed/htmlmixed.js'))
        fragment.add_javascript(load_resource('static/js/codemirror/mode/javascript/javascript.js'))
        fragment.add_javascript(load_resource('static/js/codemirror/mode/css/css.js'))
        fragment.add_css(load_resource('static/js/codemirror/lib/codemirror.css'))

        # Load CodeMirror add-ons
        fragment.add_css(load_resource('static/js/codemirror/theme/mdn-like.css'))
        fragment.add_javascript(load_resource('static/js/codemirror/addon/edit/matchbrackets.js'))
        fragment.add_javascript(load_resource('static/js/codemirror/addon/edit/closebrackets.js'))
        fragment.add_javascript(load_resource('static/js/codemirror/addon/search/search.js'))
        fragment.add_javascript(load_resource('static/js/codemirror/addon/search/searchcursor.js'))
        fragment.add_javascript(load_resource('static/js/codemirror/addon/dialog/dialog.js'))
        fragment.add_css(load_resource('static/js/codemirror/addon/dialog/dialog.css'))

        # Load Studio View
        fragment.add_content(render_template('templates/complexhtml_edit.html', {'self': self}))
        fragment.add_css(load_resource('static/css/complexhtml_edit.css'))
        fragment.add_javascript(load_resource('static/js/complexhtml_edit.js'))
        fragment.initialize_js('ComplexHTMLXBlockStudio')

        return fragment

    @XBlock.json_handler
    def studio_submit(self, data, suffix=''):
        """
        Course author pressed the Save button in Studio
        """

        if len(data) > 0:

            # NOTE: No validation going on here; be careful with your code

            self.display_name = data["display_name"]
            self.body_html = data["body_html"]
            self.body_tracked = data["body_tracked"]
            self.body_json = data["body_json"]
            self.body_js = data["body_js"]
            self.body_css = data["body_css"]

            return {"submitted": "true"}

        return {"submitted": "false"}

    @staticmethod
    def workbench_scenarios():
        """A canned scenario for display in the workbench."""
        return [
            ("complexhtml",
             """<vertical_demo>
                <complexhtml/>
                </vertical_demo>
             """),
        ]