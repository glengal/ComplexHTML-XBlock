"""
ComplexHTML XBlock for edX
Author: Raymond Lucian Blaga
Description: An HTML, JavaScript and CSS Editing XBlock that records student interactions if the course author wishes it.
"""

import urllib, datetime, json, smtplib, urllib2
import matplotlib.pyplot as plt
import numpy as np
from bson import ObjectId
from pylab import *
from pymongo import MongoClient
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from email.MIMEImage import MIMEImage
from .utils import render_template, load_resource, resource_string
from django.template import Context, Template
from xblock.core import XBlock
from xblock.fields import Scope, Integer, List, String, Boolean, Dict
from xblock.fragment import Fragment

class ComplexHTMLXBlock(XBlock):


    mysql_database  = 'edxapp'
    mysql_user      = 'root'
    mysql_pwd       = ''

    display_name = String(
        display_name="ComplexHTML XBlock",
        help="This name appears in the horizontal navigation at the top of the page",
        scope=Scope.settings,
        default="ComplexHTML XBlock"
    )

    record_click = Boolean(
        help="Record student click?",
        default=True, scope=Scope.content
    )

    record_hover = Boolean(
        help="Record student hovers? (Note that this will flood the database; use with caution)",
        default=False, scope=Scope.content
    )

    tick_interval = Integer(
        default=60000,
        help="The time (in ms) between pings sent to the server (tied to sessions above)",
        scope=Scope.content
    )

    dev_stuff = Boolean(
        help="Show chx_dev_stuff div in LMS?",
        default=False, scope=Scope.content
    )

    dependencies = String(
        help="List of JS and CSS dependencies to be used in this XBlock",
        default="", scope=Scope.content
    )

    body_html = String(
        help="HTML code of the block",
        default="<p>Body of the block goes here...</p>", scope=Scope.content
    )

    body_tracked = String(
        help="List of tracked elements",
        default="p", scope=Scope.content
    )

    body_js_chunk_1 = String(
        help="JavaScript code for the block",
        default="console.log(\"Code before onload.\");", scope=Scope.content
    )

    body_js_chunk_2 = String(
        help="JavaScript code for the block, chunk #2",
        default="console.log(\"Onload event!\");", scope=Scope.content
    )

    body_json = String(
        help="JSON container that can be used by the JavaScript code above",
        default="{\"sample\": { \"subsample\": \"true\" }}",
        scope=Scope.content
    )

    body_json_timestamp = String(
        help="Timestamp from the last update made to body_json",
        default="",
        scope=Scope.content
    )

    body_css = String(
        help="CSS code for the block",
        default="p { color: red }",
        scope=Scope.content
    )

    settings_student = String(
        help="Student-specific settings for student view in JSON form; initially a copy of body_json",
        default="",
        scope=Scope.user_state
    )

    settings_student_timestamp = String(
        help="Timestamp from the last update made to settings_student",
        default="",
        scope=Scope.user_state
    )

    grabbed = List(
        help="Student interaction that was grabbed from XBlock.",
        default=[], scope=Scope.user_state
    )

    sessions = List(
        default=[],
        help="List containing data on each session (ie, start time, end time)",
        scope=Scope.user_state
    )

    session_ended = Boolean(
        default=False,
        help="Has the student ended the current session yet?",
        scope=Scope.user_state
    )

    completed = Boolean(
        help="Completion status of this slide for the student.",
        default=False, scope=Scope.user_state
    )

    qz_attempted = Dict(
        help="Record how many attempts student have made",
        default={}, scope=Scope.user_state
    )
    n_user_id = String(
	display_name="UserId", default="0", scope=Scope.user_state, help="Id of the current user"
    )

    has_score = True
    icon_class = 'other'

    @XBlock.json_handler
    def get_dependencies(self, data, suffix=''):
        return {"dependencies": self.dependencies}

    @XBlock.json_handler
    def get_body_html(self, data, suffix=''):
        return {"body_html": self.body_html}

    @XBlock.json_handler
    def get_body_css(self, data, suffix=''):
        return {"body_css": self.body_css}

    @XBlock.json_handler
    def get_body_js(self, data, suffix=''):
        return {"body_js": ("Chunk 1: \n" + self.body_js_chunk_1 + "\nChunk 2:\n" + self.body_js_chunk_2)}

    @XBlock.json_handler
    def get_body_json(self, data, suffix=''):
        return {"body_json": self.body_json}

    @XBlock.json_handler
    def get_settings_student(self, data, suffix=''):
        return {"json_settings": self.settings_student}

    @XBlock.json_handler
    def get_grabbed_data(self, data, suffix=''):
        return {"grabbed_data": self.grabbed}

    @XBlock.json_handler
    def get_completion_status(self, data, suffix=''):
        return {"completed": self.completed}

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

        print ("CHX: Grabbed data from student: " + str(data))

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

        print ("= ComplexHTML: Grabbed data on " + self.grabbed[-1][0])
        for i in self.grabbed[-1][1]:
            print ("= ComplexHTML: +--" + str(i))

        return content

    @XBlock.json_handler
    def get_user_data(self, data, suffix=''):
        """
        Get student data from the DB
        """
        import dbconnection

        # init default data
        user_id    = "None"
        course_id  = "None"
        user_name  = "None"
        user_email = "None"
        course_ids = "None"
        user_score = "0"
        # user and course
        db = dbconnection.mysql('localhost', 3306, self.mysql_database, self.mysql_user,self.mysql_pwd)
        q = "SELECT id, user_id, course_id FROM student_anonymoususerid WHERE anonymous_user_id='" + self.n_user_id + "'"
        db.query(q)
        res = db.fetchall()
        for row in res:
            user_id   = row[1]
            course_id = row[2]
        print user_id
        q = "SELECT course_id FROM student_courseenrollment WHERE user_id='%s' " % (user_id)
        db.query(q)
        res = db.fetchall()
        for row in res:
            course_ids = row[0]
        print course_ids
        labels = [course_ids, "System"]
        data =   [3.75               , 4.75]
        error =  [0.3497             , 0.3108]
        xlocations = np.array(range(len(data)))+0.5
        width = 0.5
        bar(xlocations, data, yerr=error, width=width)
        yticks(range(0, 8))
        xticks(xlocations+ width/2, labels)
        xlim(0, xlocations[-1]+width*2)
        title("Average Ratings on the Training Set")
        gca().get_xaxis().tick_bottom()
        gca().get_yaxis().tick_left()
        savefig('/tmp/test.png')
        # username
        q = "SELECT name FROM auth_userprofile WHERE user_id='%s' " % (user_id)
        db.query(q)
        res = db.fetchall()
        for row in res:
            #print row
            user_name = row[0]
        #print user_name
        # email
        q = "SELECT email FROM auth_user WHERE id='%s' " % (user_id)
        db.query(q)
        res = db.fetchall()
        for row in res:
            user_email   = row[0]
        strFrom = 'test@online.cdot.senecacollege.ca'
        strTo = 'to@example.com'
        msgRoot = MIMEMultipart('related')
        msgRoot['Subject'] = 'test message'
        msgRoot['From'] = strFrom
        msgRoot['To'] = strTo
        msgRoot.preamble = 'This is a multi-part message in MIME format.'
        msgAlternative = MIMEMultipart('alternative')
        msgRoot.attach(msgAlternative)
        message = MIMEText('<b>Some <i>HTML</i> text</b> and an image.<br><img src="cid:image1"><br>Nifty!', 'html')
        msgAlternative.attach(message)
        msgRoot.attach(msgAlternative)
        fp = open('/tmp/test.png', 'rb')
       	msgImage = MIMEImage(fp.read())
      	fp.close()
        msgImage.add_header('Content-ID', '<image1>')
        msgRoot.attach(msgImage)
        try:
            #print ("INside")
            smtpObj = smtplib.SMTP('localhost', 25)
            smtpObj.ehlo()
            smtpObj.sendmail(strFrom, strTo, msgRoot.as_string())
            smtpObj.quit()
            #print ("Success")
        except:
            print ("Error")
        return {'user': user_email}
    def mongo_connection(self, data, collection):
        """
        Connection to mongodb
        """
        if collection != "":
            print ("Before mongo")
            client = MongoClient()
            db = client.edxapp
            if data and collection == "quizzes":
                for dict in data:
                    for slideId in dict:
                        print (dict.get(slideId).get("quizId"))
            elif data and collection == "students":
                if db.students.find({"student_id" : data["student_id"], "quizzes": data["quizid"]}):
                    mongo_attempt = db.students.find({"attempts" : data["attempts"]})
                    for dict_attempt in mongo_attempt:
                        print ("Dict attempt")
                        print (dict_attempt["attempts"])
                        #TODO attempts reload options
                        attempt = int(dict_attempt["attempts"])
                        attempt += 1
                    db.students.update({"attempts": data['attempts']} , {"$set": {"attempts" : attempt}})
                student_to_db = {"student_id": data["student_id"], "attempts": data["attempts"], "quizzes": data["quizid"]}
                db.students.insert(student_to_db)
                print ("Mongo student")
            print ("End of the mongo")
    @XBlock.json_handler
    def clear_data(self, data, suffix=''):
        """
        Clear data grabbed from student
        """
        del self.grabbed[:]
        return {"cleared": "yes"}

    @XBlock.json_handler
    def update_student_settings(self, data, suffix=''):
        """
        Update student settings from AJAX request
        """
        if self.settings_student != data["json_settings"]:
            self.settings_student = json.dumps(data["json_settings"])
            return {"updated": "true"}

        return {"updated": "false"}

    @XBlock.json_handler
    def session_start(self, data, suffix=''):
        """
        Start a new student session and record the time when it happens
        """

        self.session_ended = False
        print ("= ComplexHTML: Session started at: " + str(datetime.datetime.now()))
        self.sessions.append([str(datetime.datetime.now()), "", ""])

        return {}

    @XBlock.json_handler
    def session_tick(self, data, suffix=''):
        """
        Record a periodic tick while the student views this XBlock.
        A safety measure in case their browser or tab crashes.
        """

        if len(self.sessions) > 0:

            if not self.session_ended:

                print ("= ComplexHTML: Session tick at: " + str(datetime.datetime.now()))
                self.sessions[-1][1] = str(datetime.datetime.now())

        return {}

    @XBlock.json_handler
    def session_end(self, data, suffix=''):
        """
        End a student session and record the time when it happens
        """

        if len(self.sessions) > 0:

            if not self.session_ended:

                print ("= ComplexHTML: Session ended at: " + str(datetime.datetime.now()))
                self.sessions[-1][2] = str(datetime.datetime.now())
                self.session_ended = True

        return {}

    @staticmethod
    def get_num_sessions(self):
        return len(self.sessions)

    @XBlock.json_handler
    def complete_block(self, data, suffix=''):
        """
        Mark this XBlock as completed for the student
        """
        self.completed = True
        return {}

    @staticmethod
    def url_loader(strin, sep):
        """
        Load contents of all URLs from strin, separated by sep and return a compiled string
        """
        strout = ""

        for line in strin.split(sep):
            if line[:4] == "http":
                strout += urllib.urlopen(line).read().decode('utf-8')
            # else ignore line

        return strout

    @staticmethod
    def generate_html(html):

        result = "<div class=\"complexhtml_xblock\">"
        # Assume valid HTML code
        result += html
        result += "</div>"

        return result

    @staticmethod
    def generate_js(self, jsa, jsb, tracked="", record=[]):

        # Load first chunk of the JS script
        # result = load_resource('static/js/complexhtml_lms_chunk_1.js')
        result = render_template('static/js/complexhtml_lms_chunk_1.js', {'self': self})

        # Generate AJAX request for each element that will be tracked
        tracked_str = ""

        for i in tracked.split("\n"):

            if "click" in record:
                e = i.split(", ")
                tracked_str += "recordClick(\'" + e[0] + "\'"
                if len(e) > 1:
                    tracked_str += ", \'" + e[1] + "\'"
                tracked_str += ");\n"

            if "hover" in record:
                e = i.split(", ")
                tracked_str += "recordHover(\'" + e[0] + "\'"
                if len(e) > 1:
                    tracked_str += ", \'" + e[1] + "\'"
                tracked_str += ");\n"

        # Adding tracking calls
        result += "/* Elements being recorded go here */\n" + tracked_str

        # Add first staff entered chunk - ie the code running before the onLoad
        result += "\n\n/* Staff entered JS code */\n"
        result += "try {\n"
        result += "eval(\"" + jsa.replace("\"", "\\\"").replace("\'", "\\\'").replace("\n", "\\n\" + \n\"") + "\"\n);"
        result += "\n\n} catch (err) {\n"
        result += "    console.log(\"ComplexHTML caught this error in pre-run JavaScript code: \" + err);\n"
        result += "    $(\'.chx_javascript_error\').show();\n"
        result += "    $(\'.complexhtml_xblock\').hide();\n"
        result += "}\n"

        # Add second JavaScript chunk
        # result += "\n" + load_resource('static/js/complexhtml_lms_chunk_2.js')
        result += "\n" + render_template('static/js/complexhtml_lms_chunk_2.js', {'self': self})

        # Add second staff entered chunk - ie the code running on page load
        result += "\n/* Staff entered JS code */\n"
        result += "try {\n"
        result += "eval(\"" + jsb.replace("\"", "\\\"").replace("\'", "\\\'").replace("\n", "\\n\" + \n\"") + "\"\n);"
        result += "\n\n} catch (err) {\n"
        result += "    console.log(\"ComplexHTML caught this error in pre-run JavaScript code: \" + err);\n"
        result += "    $(\'.chx_javascript_error\').show();\n"
        result += "    $(\'.complexhtml_xblock\').hide();\n"
        result += "}\n"
        result += "\n})\n\n}"

        return result

    @staticmethod
    def generate_css(css, preview=False):

        result = ""
        tmp = css

        if preview:
            block_name = ".complexhtml_preview"
        else:
            block_name = ".complexhtml_xblock"

        # Prefix all CSS entries with XBlock div name to ensure they apply
        for i in tmp.split('\n'):
            if i.find('{') != -1:
                result += block_name + " " + i
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
            content["css"] = self.generate_css(self.body_css, true)
            return content
        return content

    @staticmethod
    def generate_dependencies(dependencies):
        """
        Generate HTML tags for JS and CSS dependencies
        """

        css_pile = ""
        js_pile = ""

        # load JS and CSS dependencies
        for line in dependencies.split('\n'):

            if line[:4] == "http":

                if line[-4:] == ".css":
                    css_pile += "<link rel=\"stylesheet\" href=\"" + line + "\" />\n"

                if line[-3:] == ".js":
                    js_pile += "<script src=\"" + line + "\"></script>\n"

                # else ignore; not a valid asset

            # else ignore; not a valid link

        return css_pile + js_pile

    @XBlock.json_handler
    def get_generated_dependencies(self, data, suffix=''):
        """
        Generate HTML tags for JS and CSS dependencies and return them via AJAX request
        """
        content = {"dependencies": ""}
        if self.dependencies != "":
            content["dependencies"] = self.generate_dependencies(self.dependencies)
            return content
        return content

    @staticmethod
    def update_student_settings_backend(source, settings):
        """
        Returns dictionary that is source merged with settings
        """
        result = json.loads(source)
        result.update(json.loads(settings))
        return json.dumps(result)

    @XBlock.json_handler
    def get_clean_body_json(self, data, suffix=''):
        body_json = json.loads(self.settings_student)
        return {"body_json_clean": body_json}

    def get_student_id(self):
        """
         Get data from student_id
        """
        if hasattr(self, "xmodule_runtime"):
            s_id = self.xmodule_runtime.anonymous_student_id
        else:
            if self.scope_ids.user_id == None:
                s_id = "None"
            else:
                s_id = unicode(self.scope_ids.user_id)
        return s_id

    @XBlock.json_handler
    def get_quiz_attempts(self, data, suffix =''):
        correct_and_reason = {}
        quiz_attempts = {}
        attempt = 0
        body_json = json.loads(self.body_json)
        quizId = 0
        student_id = self.get_student_id()
        print("Student_id")
        print(student_id)
        if data['ch_question']:
            print ("Ch_question")
            print (data['ch_question'])
            for key, value in data['ch_question'].iteritems():
                if key == "selectedQuizId":
                   quizId = int(value)
            quiz_attempts.update({'student_id' : student_id, 'quizid' : quizId, 'attempts' : attempt})
            self.mongo_connection(quiz_attempts, "students")
            self.qz_attempted = data['ch_question'].copy()
            self.get_conditionals()
        for item in xrange(len(body_json["quizzes"])):

            if item == int(self.qz_attempted["selectedQuizId"]):
                if int(self.qz_attempted['correct']) == int(self.qz_attempted['selected']):
                    correct_and_reason.update({'correct': 'true'})
                else:
                    correct_and_reason.update({'correct': 'false'})
        print("Queue")
        print("Before")
        print quiz_attempts
        print("End of attempts")
        return {"quiz_result_id": correct_and_reason}

    def get_conditionals(self):
        """
        Get conditionals from instructor
        """
        conditionals = []
        print("SELF")
        con_json = json.loads(self.body_json)
        if con_json["conditions"]:
            for condition in con_json["conditions"]:
                conditionals.append(condition)
            for condition in conditionals:
                print (condition)
            self.mongo_connection(conditionals, "quizzes")
        return {"quiz_ids" : {} , "slideIds" : {}}

    def student_view(self, context=None):
        """
        The student view
        """

        fragment = Fragment()
        content = {'self': self}
        self.n_user_id = self.get_student_id()

        # copy over body_json to settings_student if the latter is blank
        if self.settings_student == "":
            self.settings_student_timestamp = self.body_json_timestamp
            self.settings_student = self.body_json

        # settings_student isn't blank
        else:

            # compare timestamps
            if self.settings_student_timestamp != self.body_json_timestamp:

                # settings_student is outdated in this case, it must be updated
                self.settings_student = self.update_student_settings_backend(self.settings_student, self.body_json)
                self.settings_student_timestamp = self.body_json_timestamp

            # else all is in order, keep going

        body_html = self.generate_dependencies(self.dependencies) + unicode(self.generate_html(self.body_html))

        fragment.add_css(unicode(self.generate_css(self.body_css)))
        fragment.add_css(load_resource('static/css/complexhtml.css'))

        fragment.add_content(Template(body_html).render(Context(content)))
        fragment.add_content(render_template('templates/complexhtml.html', content))

        record = []

        if self.record_click:
            record.append("click")
        if self.record_hover:
            record.append("hover")

        fragment.add_javascript(unicode(
            self.generate_js(
                self,
                self.body_js_chunk_1,
                self.body_js_chunk_2,
                self.body_tracked,
                record
            )
        ))
        fragment.initialize_js('ComplexHTMLXBlock')

        return fragment

    def studio_view(self, context=None):
        """
        The studio view
        """

        fragment = Fragment()
        content = json.loads(load_resource("static/studio_settings.json"))
        content['self'] = self

        try:
            urllib2.urlopen(content["CKEDITOR_URL"])
        except urllib2.HTTPError, e:
            content["CKEDITOR_URL"] = ""
        except urllib2.URLError, e:
            content["CKEDITOR_URL"] = ""

        if self.tick_interval < 1000:
            self.tick_interval = 86400000  # 24 hrs

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
        fragment.add_content(render_template('templates/complexhtml_edit.html', content))
        fragment.add_css(load_resource('static/css/complexhtml_edit.css'))
        fragment.add_javascript(unicode(render_template('static/js/complexhtml_edit.js', content)))
        fragment.initialize_js('ComplexHTMLXBlockStudio')

        return fragment

    @staticmethod
    def generate_preview(self, dependencies, html, json, jsa, jsb, css):

        preview = ""

        # disabled for now due to time constraints

        #preview += self.generate_dependencies(dependencies)

        # style tag

        #preview += self.generate_css(css, True)

        # style tag

        # script tag

        # json_settings = { contents of json from arguments }

        # jsa

        # function preview_run() {
        #   jsb
        # };

        # script tag

        # ".complexhtml_preview" div

        #preview += self.generate_html(html)

        # ".complexhtml_preview" div

        return preview

    @XBlock.json_handler
    def studio_submit(self, data, suffix=''):
        """
        Course author pressed the Save button in Studio
        """

        result = {"submitted": "false", "saved": "false", "message": "", "preview": ""}

        if len(data) > 0:

            # Used for the preview feature
            # if data["commit"] == "true":

            # NOTE: No validation going on here; be careful with your code
            self.display_name = data["display_name"]
            self.record_click = data["record_click"] == 1
            self.record_hover = data["record_hover"] == 1
            self.tick_interval = int(data["tick_interval"])
            self.dev_stuff = data["dev_stuff"] == 1
            self.dependencies = data["dependencies"]
            self.body_html = data["body_html"]
            self.body_tracked = data["body_tracked"]
            self.body_json = data["body_json"]
            self.body_json_timestamp = str(datetime.datetime.now())
            self.body_js_chunk_1 = data["body_js_chunk_1"]
            self.body_js_chunk_2 = data["body_js_chunk_2"]
            self.body_css = data["body_css"]

            if self.tick_interval < 1000:
                self.tick_interval = 86400000  # 24 hrs

            result["submitted"] = "true"
            result["saved"] = "true"

            ''' # Used for previewing feature
            elif data["commit"] == "false":

                result["submitted"] = "true"
                result["preview"] = self.generate_preview(
                    self,
                    data["dependencies"],
                    data["body_html"],
                    data["body_json"],
                    data["body_js_chunk_1"],
                    data["body_js_chunk_2"],
                    data["body_css"]
                )

            else:
                print ("Invalid commit flag. Not doing anything.")

            '''

        return result

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
