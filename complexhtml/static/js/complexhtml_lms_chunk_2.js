console.log("complex js chunk2");
/* Page is loaded. Do something. */
$(function ($) {
    console.log("on page load from chunk2");
    getCleanBody(function(){
        console.log("Before");
        console.log("After");
        anySlide = new AVIATION.common.Slide();
        anySlide.constructor(json_clean_setting);
        console.log("JSON");
        console.log(json_clean_setting);
        json_clean_setting.parentSlide = anySlide;
        $(anySlide).on("completedQuiz", function(selectedAnswers){
    		$(".answers input:checked").each(function(index, value){
            console.log('wow');
            console.log($(this).attr('id'));
            checked = $(this).attr('id');
            });
            console.log("checked");
            console.log(checked);
            var sel = checked.split('_');
            var selected = sel[3];

	    console.log("Got");
        checkQuizResult(checked,selected);
	    sendEmail();
        });
    });

tick_timer = setInterval(function() {
        $.ajax({
            type: "POST",
            url: runtime.handlerUrl(xblock_element, 'session_tick'),
            data: JSON.stringify({}),
            async: false
        });
    }, session_tick);

$(window).unload(function() { session_end(); });
$('.chx_end_session').click(function() { session_end(); });
