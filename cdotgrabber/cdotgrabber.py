"""TO-DO: Write a description of what this XBlock is."""

import urllib, datetime, json
from .utils import render_template, load_resource, resource_string
from django.template import Context, Template
from xblock.core import XBlock
from xblock.fields import Scope, Integer, List, String
from xblock.fragment import Fragment


class CDOTgrabberXBlock(XBlock):
    """
    Simple XBlock that grabs
    """

    display_name = String(
        display_name="CDOT Slide",
        help="This name appears in the horizontal navigation at the top of the page",
        scope=Scope.settings,
        default="CDOT Slide"
    )

    body_html = String(
        help="HTML body of the slide",
        default="<p class=\"grabber_default\">Body of slide goes here...</p>", scope=Scope.content
    )

    body_js = String(
        help="JS code for the slide",
        default="console.log(\"Your lack of JavaScript disturbs me.\");", scope=Scope.content
    )

    body_json = String(
        help="JSON code for the slide used to initialize fields",
        default="{\"blank\": { \"not_really_blank\": \"true\" }}", scope=Scope.content
    )

    body_css = String(
        help="CSS code for the slide",
        default=".grabber_default { color: red }", scope=Scope.content
    )

    grabbed = List(
        default=[], scope=Scope.user_state,
        help="Student interaction that was grabbed from XBlock.",
    )

    @XBlock.json_handler
    def grab_data(self, data, suffix=''):
        """
        Grab all data passed from cdotgrabber.js and append it to self.grabbed.
        """

        content = {"time": str(datetime.datetime.now())}
        chunk = []

        for i in data: chunk.append((str(i), str(data[i])))

        if len(chunk) > 0:
            self.grabbed.append((content["time"], chunk))
            content["data"] = chunk

        else:
            self.grabbed.append((content["time"], "crickets"))
            content["data"] = None

        print "Grabbed data on " + self.grabbed[-1][0]
        for i in self.grabbed[-1][1]: print "+--" + str(i)

        return content

    def student_view(self, context=None):
        """
        The student view
        """

        fragment = Fragment()
        content = {'self': self}

        # Build page based on user input HTML, JS and CSS code

        if self.body_html[:4] == "http":
            body_html = urllib.urlopen(self.body_html).read()

        else:
            body_html = "<div class=\"cdotgrabber_xblock\">" + self.body_html + "</div>"

        if self.body_js[:4] == "http":
            body_js = urllib.urlopen(self.body_js).read()
        else:
            body_js = load_resource('static/js/cdotgrabber.js')
            body_js = body_js[:-7] + self.body_js + body_js[-7:]

        if self.body_css[:4] == "http":
            body_css = urllib.urlopen(self.body_css).read()
        else:
            body_css = self.body_css

        print(body_js)

        fragment.add_content(Template(unicode(body_html)).render(Context(content)))
        fragment.add_javascript(unicode(body_js))
        fragment.add_css(unicode(body_css))

        # FOR DEVELOPMENT
        fragment.add_content(render_template('templates/cdotgrabber.html', content))
        fragment.add_css(load_resource('static/css/cdotgrabber.css'))
        # FOR DEVELOPMENT

        fragment.initialize_js('CDOTgrabberXBlock')

        return fragment

    def studio_view(self, context=None):
        """
        The studio view
        """

        fragment = Fragment()
        fragment.add_content(render_template('templates/cdotgrabber_studio.html', {'self': self}))
        fragment.add_css(load_resource('static/css/cdotgrabber_studio.css'))
        fragment.add_javascript(load_resource('static/js/cdotgrabber_studio.js'))
        fragment.initialize_js('CDOTgrabberXBlockStudio')

        return fragment

    @XBlock.json_handler
    def studio_submit(self, data, suffix=''):

        print "Snatched input from Studio View"

        #TODO process JSON code here

        if len(data) > 0:

            # NOTE: No validation going on here; be careful with your code

            self.display_name = data["display_name"]
            self.body_html = data["body_html"]
            self.body_json = data["body_json"]

            # json processing
            fields = json.loads(self.body_json)
            print fields


            self.body_js = data["body_js"]
            self.body_css = data["body_css"]

            '''
            print("+ Submitted data")
            print("+- Display Name: " + data["display_name"])
            print("+- HTML: " + data["body_html"])
            print("+- JS: " + data["body_js"])
            print("+- JSON: " + data["body_json"])
            print("+- CSS: " + data["body_css"])
            '''

            return {"submitted": "true"}

        return {"submitted": "false"}

    @staticmethod
    def workbench_scenarios():
        """A canned scenario for display in the workbench."""
        return [
            ("CDOTgrabberXBlock",
             """<vertical_demo>
                <cdotgrabber/>
                </vertical_demo>
             """),
        ]
