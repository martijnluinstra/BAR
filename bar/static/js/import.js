var insert_rows = function(columns)
{
	var nrows = columns[0].rows.length;

	var table = $('#import-table tbody');

	var template = table.find('tr').detach();

	for (var i = 0; i < nrows; ++i)
		table.append(template.clone().each(function() {
			this.id = 'row' + i;
		}));
};

var populate_selects = function(columns)
{
	var selects = $('#import-table thead select');

	selects.each(function() {
		var select = $(this);

		var name = select.prop('name');

		select.append($('<option>').val('empty').text(''));
		
		$.each(columns, function(i, column) {
			select.append($('<option>').val(i).text(column.header));	
		});

		select.change(function(e) {
			var val = $(this).val();

			switch (val) {
				case 'empty':
					populate_column(name, '');
					break;

				default:
					populate_column(name, columns[$(this).val()].rows);
					break;
			}
		});
	});
};

var populate_column = function(prop, value)
{
	var fields = $("#import-table tbody *[name='" + prop + "']");

	fields.each(function(row) {
		switch ($(this).attr('type')) {
			case 'checkbox':
				$(this).prop('checked', !!value);
				break;
			default:
				console.log(typeof value[row] !== 'string');
				if ($.isArray(value) && typeof value[row] !== 'string'){
					$(this).val(value[row][0]);
					if(prop == 'name'){
						$(this).prop('title', 'Name already exists in the database: '+value[row][1].join(' '))
						.closest('td').addClass('invalid nonunique');
					}
				}else if ($.isArray(value)){
					$(this).val(value[row]);
				}else{
					$(this).val(value);
				}
				break;
		}
		
	});
};

var submit = function()
{
	var rows = {};

	$('#import-table > tbody > tr').each(function() {
		var row = {};

		// Ignore unchecked rows
		if (!$(this).find('input[name=import]').is(':checked'))
			return;

		// Add all the fields to the row object
		$(this).find('input').each(function() {
			var val = $(this).val();

			if ($(this).attr('type') == 'checkbox' && !$(this).is(':checked'))
				val = false;

			row[$(this).attr('name')] =  val;
		});

		// Finally 
		rows[this.id] = row;
	});

	//Clear all flags
	$('#import-form tbody td').removeClass();
	$('#import-form tbody td input').prop('title', '');

	$.ajax($('#import-form').attr('href'),{
            data : JSON.stringify(rows),
            contentType : 'application/json',
            headers: {'X-CSRFToken': window.csrf_token},
            type : 'POST' 
	    }).success( function(response) {
			if (response.length == 0) {
				document.location.href = window.urls.list_participants;
				return;
			}

			$.map(response, function(fields, row) {
				$.map(fields, function(errors, field) {
					$("#" + row + " input[name='" + field + "']")
						.prop('title', 'Invalid ' + errors.join(', '))
						.closest('td').addClass(['invalid'].concat(errors).join(' '));
				});
			});

			alert('Your data is incomplete, please fix the highlighted fields!');
		});
};

$('#import-form').submit(function(e) {
	e.preventDefault();
	submit();
});

$('#import-form thead > tr > th:first-child input').change(function() {
	$('#import-form tbody > tr > td:first-child input').prop('checked', $(this).prop('checked'));
});

if (window.import_data)
{
	insert_rows(window.import_data);

	populate_selects(window.import_data);
}
