var current = {};
var delta = {};
var model = {
    purchases: [],
    undos: []
};
var timers = {};
var config = {
    error_message: 'Something went wrong? See the console, or ask Martijn!',
    history_size: 10
};

function format_exchange(amount){
    return "€ "+(amount/100).toFixed(2)
}

$('#view-users .table-bar tr').each(function() {
    current[this.id] = parseInt($(this).data('spend-amount'));
});

$("#view-users .table-bar button[data-type^='purchase']").click(function(evt){
    evt.preventDefault();
    evt.stopPropagation()
    // Get me some data
    var field = $(this).closest('tr').find('td').get(1);
    var spinner = $(this).closest('td').find('.spinner').get(0);
    var participant_id = $(this).data('participant-id');
    var product_id = $(this).data('product-id');
    var product_price = $(this).data('price');
    var is_eligible = $(this).data('is-eligible');
    var amount = parseInt($($(spinner).find('input').get(0)).val());

    if (isNaN(amount)) amount = 1;

    if (!is_eligible){
        var proceed = confirm($(this).closest('tr').find('td').get(0).innerHTML + ' is too young to buy this product! Are you sure you want to continue?');
        if(!proceed) return;
    }

    // Update the users delta and current amount of x-es
    for(var i=0;i<amount;i++){
        model['purchases'].push({participant_id: participant_id, product_id: product_id, price: product_price});
        delta[participant_id] = (delta[participant_id] || 0) + product_price;
    }
    $(field).text(format_exchange(current[participant_id] + delta[participant_id]));

    //reset spinner
    spinner_reset(spinner);

    // If there is a sync-request queued for this user, delete it.
    if (timers['purchases'])
        clearTimeout(timers['purchases']);

    // Queue a sync-request for this user
    timers['purchases'] = setTimeout(create_sync_task('/purchases', 'purchases'), 1000);
    $('#search').focus();
});

function create_sync_task(url, item) {
    return function() {
        // Run the request
        var submitted_items = model[item];
        $.ajax({
            url: url,
            type: "POST",
            data: JSON.stringify(model[item]),
            contentType: "application/json",
            headers: {'X-CSRFToken': window.csrf_token},
            timeout: 5000
        }).fail(function(response){
            model[item].concat(submitted_items);
            for(var i in submitted_items){
                var participant_id = i['participant_id'];
                delta[participant_id] = (delta[participant_id] || 0) + i['price'];
                current[participant_id] -= i['price'];
            }
            alert(config['error_message']);
        });

        console.log('Submitted', model[item], 'to', url);

        // commit locally
        for(var i in model[item]){
            current[i['participant_id']] += i['price'];
            delete delta[i['participant_id']];
        }
        model[item] = new Array();
        delete timers[item];
    }
};

$("#view-users  .table-bar button[data-type^='history']").click(function(evt){
    evt.preventDefault();
    var participant_id = $(this).data('participant-id');
    url='/participants/' + participant_id + '/history?limit='+config['history_size']+'&timestamp='+ new Date().getTime();

    $.get(url, {timeout: 3000}, function( data ) {
            show_history_modal($(data).filter('.content'), participant_id);
        }).fail(function(response){
        alert(config['error_message']);
    });

    $('#search').focus();
});

function show_history_modal(data, participant_id){
    title = data.find('.content-header>h1').html();
    body = data.find('.table-bar');
    body.find("a[data-type^='undo']").click(function(evt){
        evt.preventDefault();

        var participant_id = $(this).data('participant-id');
        var purchase_id = $(this).data('purchase-id');
        var product_price = $(this).data('price')*-1;
        var field = $('.table-bar tr#'+participant_id).find('td').get(1);

        // Update the users delta and current amount of x-es
        model['undos'].push({participant_id: participant_id, purchase_id: purchase_id, price: product_price});
        delta[participant_id] = (delta[participant_id] || 0) + product_price;
        $(field).text(format_exchange(current[participant_id] + delta[participant_id]));

        // If there is a sync-request queued for this user, delete it.
        if (timers['undos'])
            clearTimeout(timers['undos']);

        // Queue a sync-request for this user
        timers['undos'] = setTimeout(create_sync_task('/purchases/undo', 'undos'), 1000);

        $(this).addClass('disabled');
    });
    var btn_more = $('<a href="/participants/' + participant_id + '/history" class="btn btn-default">Complete history</a>');
    $('#barModal').find('.modal-title').show().html(title);
    $('#barModal').find('.modal-body').hide().empty();
    $('#barModal').find('.modal-table').show().empty().append(body);
    $('#barModal').find('.modal-footer').show().empty().append(btn_more).append('<button class="btn btn-primary" data-dismiss="modal">Ok</button>');
    $('#barModal').find('.modal-dialog').removeClass("modal-lg");
    $('#barModal').modal('show');
};

/* Search */

// Case insensitive contains filter
jQuery.expr[':'].containsNCS = function(a, i, m) {
  return jQuery(a).text().toUpperCase()
      .indexOf(m[3].toUpperCase()) >= 0;
};

$('#view-users  #search').focus();
$(document).click(function(evt) { 
    if (! $(evt.target).is( ".spinner input" ))
        $('#search').focus();
});


$('.form-search').submit(function(evt) {
    evt.preventDefault();
});

$('#view-users  #search').keyup(function(evt) {
    var query = $(this).val();
    $('.table-bar tbody tr').hide();
    $('.table-bar tbody tr td:first-child:containsNCS('+ query +')').closest('tr').show();
    if (evt.key === 'Enter') {
        var clean = query.split(window.uuid_prefix)
        if (window.uuid_prefix && clean.length > 1)
            $('.table-bar tbody tr[data-uuid="'+ clean[1] +'"]').show();
        else
            $('.table-bar tbody tr[data-barcode="'+ query +'"]').show();
        $(this).val('');
    }
});

/* FAQ */

$("nav a[data-type^='faq']").click(function(evt){
    evt.preventDefault();
    var url = $(this).attr('href');
    $.get(url, {timeout: 3000}, function( data ) {
            show_info_modal($(data).filter('#panel-content'));
        }).fail(function(response){
        alert(config['error_message']);
    });
});

function show_info_modal(data){
    title = data.find('h1#panel-title').html();
    body = data.find('#panel-content').html();
    $('#barModal').find('.modal-title').show().html(title);
    $('#barModal').find('.modal-body').show().html(body);
    $('#barModal').find('.modal-table').hide().empty();
    $('#barModal').find('.modal-footer').show().html('<button class="btn btn-primary" data-dismiss="modal">Ok</button>');
    $('#barModal').find('.modal-dialog').addClass("modal-lg");
    $('#barModal').modal('show');
};

/* Spinner */

$('.spinner .btn:first-of-type').click(function(evt) {
    evt.preventDefault();
    spinner_update($(this).closest('.spinner'), 1);
});
$('.spinner .btn:last-of-type').click(function(evt) {
    evt.preventDefault();
    spinner_update($(this).closest('.spinner'), -1);
});
    
$('.spinner input').keyup(function(evt) {
    if(isNaN(parseInt($(this).val())) && $(this).val()!='') $(this).val(1);
});

function spinner_reset(spinner){
    $($(spinner).find('input').get(0)).val(1);
}

function spinner_update(spinner, mod){
    var input = $(spinner).find('input').get(0);
    var value = parseInt($(input).val(), 10) + mod;
    if(isNaN(value)) value = 1;
    if($(input).data('min') !== undefined) value = (value < $(input).data('min') ? $(input).data('min') : value);
    if($(input).data('max') !== undefined) value = (value > $(input).data('max') ? $(input).data('max') : value);
    $(input).val(value);
}

$('.block-screen').hide();

if($('#view-users').length !== 0){
    $(window).bind('beforeunload', function(){
        if (timers['purchases']){
            clearTimeout(timers['purchases']);
            var task = create_sync_task('/purchases', 'purchases');
            task();
        }
        if (timers['undos']){
            clearTimeout(timers['undos']);
            var task = create_sync_task('/purchases/undo', 'undos');
            task();
        }

        if (timers['leave'])
            clearInterval(timers['leave']);

        if ($.active>0){
            $('.block-screen').show();
            timers['leave'] = setInterval(function(){
                if ($.active==0){
                    $('.block-screen').hide();
                    clearInterval(timers['leave']);
                }
            }, 250);
            return 'The last changes have not been saved!\n We will lose data if you continue!';
        }
    });
}
