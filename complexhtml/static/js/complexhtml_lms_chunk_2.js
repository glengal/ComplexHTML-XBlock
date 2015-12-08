/* Page is loaded. Do something. */
$(function ($) {

    getCleanBody(function(){
        anySlide = new AVIATION.common.Slide();
        $(anySlide).on("getGraphData", function(e,studentGraph){
            kcsForGraph(studentGraph);
        });
        anySlide.constructor(json_clean_setting);
        var patternId = 0;
        var actionId = false;
        json_clean_setting.parentSlide = anySlide;
        $(anySlide).on("completedQuiz", function(e,options){

            if(options && options.type ===  "action"){
                patternId = options.patternId;
                actionId = options.actionId;
                // id variable is now the id of the pattern only
                // otherwise should all be quiz related
            } else {
                $(".answers input:checked").each(function(index, value){
                    checked = $(this).attr('id');
                });
                var sel = checked.split('_');
                var selected = sel[3];
                checkQuizResult(checked,selected, patternId, actionId);
                //sendEmail();
                conditionals();
                kcTotalWeight();
            }
        });

    });

    if($(".action-publish") === undefined){
        session_start();
        tick_timer = setInterval(function (){
        $.ajax({
            type: "POST",
            url: runtime.handlerUrl(xblock_element, 'session_tick'),
            data: JSON.stringify({}),
            async: false
        });
    }, session_tick);
}

$(window).unload(function() { session_end(); });
$('.chx_end_session').click(function() { session_end(); });
