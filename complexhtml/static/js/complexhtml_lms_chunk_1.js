/* JavaScript for ComplexHTML XBlock. */
function ComplexHTMLXBlock(runtime, xblock_element) {


var json_settings = {};
var json_clean_setting = {};
var session_tick = parseInt("{{ self.tick_interval }}");
var tick_timer = "";

// if (typeof $("a[aria-selected=true]") !== 'undefined'){
//     console.log($("a[aria-selected=true]").attr("data-id").split("/").pop());
// }
// Load JSON settings from database
function loadSettings() {
    $.ajax({
        type: "POST",
        url: runtime.handlerUrl(xblock_element, 'get_settings_student'),
        data: JSON.stringify({}),
        success: function(result) {
            if (result.json_settings !== "") {json_settings = JSON.parse(result.json_settings);}
        },
        async: false
    });
}

// Update student settings with the contents of json_settings
function updateSettings(settings) {
    if (settings) {
        $.ajax({
            type: "POST",
            url: runtime.handlerUrl(xblock_element, 'update_student_settings'),
            data: JSON.stringify({"json_settings": settings})
        });
    } else {
        $.ajax({
            type: "POST",
            url: runtime.handlerUrl(xblock_element, 'update_student_settings'),
            data: JSON.stringify({"json_settings": json_settings})
        });
    }
}

// Record an element click to the student's database entry
function recordClick(rec, type) {

    $(rec, xblock_element).click(

        function (eventObject) {

            var id = this.tagName;
            if (this.type !== undefined) {id = this.type;}
            if (this.id !== "") {id = this.id;}
            if (this.className !== "" ) {id = this.className;}

            if ("{{ self.dev_stuff }}" === "True") {
                console.log("Student clicked on: " + id + ", of type " + this.type + ".");
            }

            if (this.type === type || type === undefined) {
                $.ajax({
                    type: "POST",
                    url: runtime.handlerUrl(xblock_element, 'grab_data'),
                    data: JSON.stringify({"id": id, "type": ((this.type !== undefined) ? this.type : this.tagName) + "_click"})
                });
            }

        });

}

// Record an element hover to the student's database entry
function recordHover(rec, type) {

    $(rec, xblock_element).hover(

        function (eventObject) {

            var id = this.tagName;
            if (this.type !== undefined) {id = this.type;}
            if (this.id !== "") {id = this.id;}
            if (this.className !== "" ) {id = this.className;}

            if (this.type === type || type === undefined) {
                $.ajax({
                    type: "POST",
                    url: runtime.handlerUrl(xblock_element, 'grab_data'),
                    data: JSON.stringify({"id": id, "type": ((this.type !== undefined) ? this.type : this.tagName) + "_hover"})
                });
            }

        });

}

// Mark this block as completed for the student
function markCompleted() {
    $.ajax({
        type: "POST",
        url: runtime.handlerUrl(xblock_element, 'complete_block'),
        data: JSON.stringify({})
    });
}

// Send the server the start of session message
function session_start() {

    loadSettings();
    clearInterval(tick_timer);

    if ($(".action-publish") === undefined) {

        $.ajax({
            type: "POST",
            url: runtime.handlerUrl(xblock_element, 'session_start'),
            data: JSON.stringify({}),
            async: false
        });

    }

}

// Send the server the end of session message
function session_end() {

    clearInterval(tick_timer);

    if ($(".action-publish") === undefined) {

        $.ajax({
            type: "POST",
            url: runtime.handlerUrl(xblock_element, 'session_end'),
            data: JSON.stringify({}),
            async: false
        });

    }

}

function sendEmail(){
    var user_id = "";
    $.ajax({
            type: "POST",
            url: runtime.handlerUrl(xblock_element, 'get_user_data'),
            data: JSON.stringify({}),
        });

}
function conditionals(){
    $.ajax({
        type: "POST",
        url: runtime.handlerUrl(xblock_element, 'to_send'),
        data: JSON.stringify({})
        });
}

function kcTotalWeight(){
    $.ajax({
        type: "POST",
        url: runtime.handlerUrl(xblock_element, 'to_send_kc'),
        data: JSON.stringify({})
        });
}
function kcsForGraph (studentGraph){
    $.ajax({
        type: "POST",
        url: runtime.handlerUrl(xblock_element, 'to_send_for_graph'),
        data: JSON.stringify({studentGraph}),
        success: function(result) {
           $(anySlide).trigger('drawGraph', result);
        }

        });
}


function checkQuizResult(selectedId, selected, patternId, actionId){
    var answer = [];
    for (var j = 0; j < anySlide.options.quizzes.length; j++){
    answer[j]= anySlide.options.quizzes[j].json.questions[0].a;
    }
    var quiz_id = $('.cdot_quiz').attr('id');
    var selectedId1 = selectedId.split('_');
    // var slide_id = $("a[aria-selected=true]").attr("data-id").split("/").pop();
    var selectedQuizId = parseInt(selectedId1[1]);
        for (var i = 0; i < answer[selectedQuizId].length; i++){
         if (answer[selectedQuizId][i].correct){
            var correct = parseInt(i);
            break;
             }
        }
var ch_question = {quiz_id, selectedQuizId, selected, correct, patternId, actionId};
    //  slide_id};
    $.ajax({
        type: "POST",
        url: runtime.handlerUrl(xblock_element, 'get_quiz_attempts'),
        data: JSON.stringify({'ch_question': ch_question}),
        success: function(result) {
           $(anySlide).trigger('checkCompleted', result);
        }
    });
}
function getCleanBody(callback){
    $.ajax({
        type: "POST",
        url: runtime.handlerUrl(xblock_element, 'get_clean_body_json'),
        data: JSON.stringify({}),
        success: function(result) {
            var json;
            json_clean_setting = result.body_json_clean;
          if(callback && typeof callback === 'function'){
            callback(json_clean_setting);
          }
        }
    });

}
