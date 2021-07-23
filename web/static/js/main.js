/* jshint esversion : 6 */

var fileData;

var textWrapper = document.querySelector('.ml12');
textWrapper.innerHTML = textWrapper.textContent.replace(/\S/g, "<span class='letter'>$&</span>");
anime.timeline({loop: true})
.add({
  targets: '.ml12 .letter',
  translateX: [40,0],
  translateZ: 0,
  opacity: [0,1],
  easing: "easeOutExpo",
  duration: 1200,
  delay: (el, i) => 500 + 30 * i
}).add({
  targets: '.ml12 .letter',
  translateX: [0,-30],
  opacity: [1,0],
  easing: "easeInExpo",
  duration: 1100,
  delay: (el, i) => 100 + 30 * i
});

const hasExtension = () => {
  let fileName = $('#upload').val();
  return (new RegExp('(' + ['csv','json'].join('|').replace(/\./g, '\\.') + ')$')).test(fileName);
};

const notification = (opt) => {
  if( !$.isEmptyObject(opt) ){
    let cls ='info';
    if( opt.type ) cls = opt.type;
    let message = "Information";
    if(opt.message){
      message = opt.message
    }
    $('.notification-container').html(`<div class="wow animate__animated animate__fadeInRight alert alert-${cls}">
                                          <a href="#" class="close" data-dismiss="alert" aria-label="close">&times;</a>
                                          <p>${message}</p>
                                      </div>`);
    setTimeout(function(){
      $('.notification-container').html(' ');
    }, 12000);
  }
}

const upload = () => {
  if(!hasExtension()) notification({
    message : 'Incorrect file. Use a csv or json file',
    type: 'danger'
  });
  else{
    $('#message').show();
    $('#next').show();
    $('.upld').hide();
    $('.box').show();
    data = event.target.files[0];
    Papa.parse(data, {
      header: true,
      dynamicTyping: true,
      complete: (results => {
        console.log(results)
        return false
        let table_data = '<table class="table table-bordered table-striped col-md-12">'; 
        table_data += "<tr>";
        Object.keys(results.data[0]).forEach(k => { table_data +=`<th>${k}</th>`; });
        table_data += "</tr>";
        let table_slice = results.data.slice(0, 9);
        table_slice.forEach(e=>{
          table_data+='<tr>';
          Object.values(e).forEach(v => { table_data +=`<td>${v}</td>`; });
          table_data+='</tr>';
        });
        table_data += "</table>";
        $("#file_table .tbl").html(table_data);
        $('#insights_table').hide();
        if($('#file_table').hasClass('col-md-7')){ 
          $('#file_table').removeClass('col-md-7'); 
        }
        $('#table').show();
        $('main .site__section').css('min-height', '40vh');
        fileData = results;
      })
    });
    }
};

const _beforeProcessDataUI  = () => {
      $('main .site__section').css('min-height', '100vh');
      $('#next').hide();
      $('.box').hide();
      $('#message').html('Please Wait while your file is processed');
      $('#loader').show();
      $('#table').hide();
      return false
}

const _afterProcessDataUI = ( val ) => {
    if(!$.isEmptyObject(val)){
      if(val.error){
         notification({
            type: 'danger',
            message: val.error
          })
         $('#loader').hide();
         $('.upld').show();
      }else{
        $('#loader').hide();
        $('.upld').show();
        $('#next').hide();
         notification({
            type: 'success',
            message: "Classification Successful. Find details in the classification folder"
          })
          table_data = `<table class="table table-bordered table-striped" style='margin:0 auto;'>`;
          table_data += `<tr>
                          <th>Sentences</th><th>Prediction</th><th>Polarity</th>
                        </tr>`;

          val.sentences.forEach((element, index) => {
          table_data +=`<tr>
                          <td>${element}</td>
                          <td>${val.predictions[index]}</td>
                          <td>${val.polarity[index]}</td>
                      </tr>`;
          });
          table_data += `</table>`;

          $('#message').html('Kindly a sample view of the result of the analysis');
          $("#file_table .tbl").html(table_data).css('border-right', '1px solid #fff');
          $('#file_table').removeClass('col-md-12').addClass('col-md-9');

          table_data = `<table class="table table-bordered table-striped">`;
          Object.keys(val.insight).forEach(key => {
            table_data+= `<tr>
                              <td>${key.toString().toUpperCase()}</td>
                              <td>${val.insight[ key ]}</td>
                          </tr>`;
          });
          table_data+= '</table>';
          $('#table').show();
          $('#insights_table .tbl').html(table_data);$('#insights_table').show();
          $('main .site__section').css('min-height', '40vh');
      }
    }else {
      notification({
        type: 'danger',
        message: "Error get prediction data"
      })
       $('#loader').hide();
       $('.upld').show();
    }
    return false;
}

const processData = () => {

 _beforeProcessDataUI()

  eel.classify(fileData.data)(val=> {
    console.log(val);
        _afterProcessDataUI( val );
  });
};

const processDataFlask = () => {
    _beforeProcessDataUI();
    let source = new SSE('/train',{
       headers:{
        'Content-Type': 'application/json',
       },
       payload: JSON.stringify(fileData.data);
    });
}

$(function () {
  $('#upload').on('change', upload);
  $('#next').hide();
  $('.box').hide();
  $('#loader').hide();
  $('#message').hide();
  $('#table').hide();
//  $('#next').bind('click', processData);
  $('#next').bind('click', processDataFlask);
//  $('#nextTrain').bind('click', processDataFlask);

  new WOW().init();
});