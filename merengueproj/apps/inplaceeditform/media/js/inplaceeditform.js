function inplaceeditform_ready($){
    $('.inplace-view-editable-field').bind("mouseenter",function(){
        $(this).addClass("edit_over");
    }).bind("mouseleave",function(){
        $(this).removeClass("edit_over");
    });

    $('.inplace-view-editable-field').dblclick(function (){
        $(this).hide();
        var tools = $(this).next('.inplace-tools');
        tools.show();
        var tools_error = tools.find('.inplace-tools-error')[0];
        var child_nodes = tools_error.childNodes;
        for (i=0; i<child_nodes.length; i++)
        {
            tools_error.removeChild(child_nodes[i]);
        }
    });

    $('.inplace-tools .cancel').click(function (){
        var inplace_tools = $(this).parent();
        inplace_tools.hide();
        inplace_tools.prev('.inplace-view-editable-field').show();
    });

    $('.inplace-tools .apply').click(function (){
        var auto_id = $(this).parent().find('.field_id').html();
        var field_name = $(this).parent().find('.field_name').html();
        var obj_id = $(this).parent().find('.obj_id').html();
        var content_type_id = $(this).parent().find('.content_type_id').html();
        var form = $(this).parent().find('.form').html();
        var filters = $.evalJSON($(this).parent().find('.filters').html());

        var value_input = $(this).parent().find('#' + auto_id);
        var value;

        if (value_input.attr('multiple'))
        {
            var options_selected = value_input.find('option:selected');
            value = [];
            for( i =0; i< options_selected.length; i++)
            {
                value[i] = options_selected[i].value;
            }
        }
        else{
            value = value_input[0].value;
        }
        var form_query = '';
        if (form)
        {
            form_query = '&form='+form;
        }
        var _self = this; 
        var data = 'id='+obj_id+'&field='+field_name+'&value='+encodeURIComponent($.toJSON(value))+'&content_type_id='+content_type_id+form_query+'&'+'filters='+$.toJSON(filters);
        $.ajax({
        data: data,
        url: "/inplaceeditform/",
        type: "POST",
        async:true,
        success: function(response){
            response = eval("("+ response +")");
            if (response.errors)
            {   
                var tools_error = $(_self).parent().find('.inplace-tools-error')[0];
                var child_nodes = tools_error.childNodes;
                for (i=0; i<child_nodes.length; i++)
                {
                    tools_error.removeChild(child_nodes[i]);
                }
                var ul = document.createElement('ul');
                ul.className = "errors";
                tools_error.appendChild(ul);
                for (var error in response)
                {
                    if (error != 'errors')
                    {
                        var li = document.createElement('li');
                        if ("'+field_name+'" == error)
                            li.innerHTML = response[error];
                        else
                            li.innerHTML = error+ ": " +response[error];
                        ul.appendChild(li);
                    }
                }
            }
            else
            {

                var inplace_tools = $(_self).parent();
                inplace_tools.hide();
                inplace_tools.prev('.inplace-view-editable-field').html(response.value)
                inplace_tools.prev('.inplace-view-editable-field').show();
                var inplace_messages = inplace_tools.prev().prev('.inplace-messages');    
                inplace_messages.fadeIn();
                window.setTimeout("jQuery('.inplace-messages').fadeOut()", 2000);
            }
        }
    });
    });
}