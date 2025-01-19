let currentTab = "tab_analysis_type";
let analysisType
showTab(currentTab)


/*
*  In base al tipo di analisi mostro tab diversi
*
*/
$('.analysis_type').click(function(e) {
  //e.preventDefault();
  next(this.id)
})


function next(clickedOn) {

  document.getElementById(currentTab).style.display = "none";
  // document.getElementById(currentTab).style.visibility= "hidden";
  // document.getElementById(currentTab).style.opacity = 0;
  console.log(clickedOn)


  if(clickedOn == "data_summary" || clickedOn =="agreement" || clickedOn=="linguistic" || clickedOn == "fleiss"){
    analysisType = clickedOn
    let title = document.getElementById("title_analysis")

    if(clickedOn == "data_summary") title.innerHTML = "Data summary"
    else if(clickedOn == "agreement") title.innerHTML = "Agreement"
    else if(clickedOn == "linguistic") title.innerHTML = "Linguistic Analysis"
    else title.innerHTML = "Fleiss"

    showTab("tab_video_selection");
  }

  else if(clickedOn == "video" && (analysisType == "data_summary" || analysisType=="linguistic")){
    showTab("tab_annotator_selection")
    document.getElementById("tab_two_annotators_selection").style.display = "none";
    document.getElementById("submitButton").style.display = "block";
  }

  else if(clickedOn == "video" && analysisType == "agreement"){
    showTab("tab_two_annotators_selection")
     document.getElementById("tab_annotator_selection").style.display = "none";
    document.getElementById("submitButton").style.display = "block";
  }

}



function showTab(id) {

  document.getElementById(id).style.visibility= "visible";
  document.getElementById(id).style.opacity= 1;
  document.getElementById(id).style.display= "block";

  currentTab = id

  // if (id == "tab_analysis_type") {
  //   document.getElementById("prevBtn").style.display = "none";
  // } else {
  //   document.getElementById("prevBtn").style.display = "inline";
  // }

  //fixStepIndicator(n)
}


/* Selezione video */
$('.video_radio').click(function(e) {
  e.preventDefault();

  let video_id = this.getAttribute("video")
  let annotators = videos_grouped[video_id].annotators

  document.getElementById(video_id).checked = true


  if(analysisType == "data_summary" || analysisType == "linguistic") {

    // document.getElementById('tab_annotator_selection').style.display = "none"
    // document.getElementById('tab_two_annotators_selection').style.display = "none"
    //document.getElementById('selected_type').innerHTML = analysisType
    document.getElementById('selected_video').innerHTML = videos_grouped[video_id].title
    document.getElementById('annotators').innerHTML = ""

    for (let i in annotators) {

      document.getElementById('annotators').innerHTML +=

          '<div className="form-check"> ' +

          '<label className="form-check-label" class="annotator-label" htmlFor="' + annotators[i].id + '">' +
          '<input className="form-check-input" class="annotator-radio" type="radio" name="annotator" ' +
            'value="' + annotators[i].id + '" id="' + annotators[i].id + '">' +
          annotators[i].name +
          '</label>' +
          '</div>'
    }
  }

  else if (analysisType == "agreement"){


    //document.getElementById('selected_type_agreement').innerHTML = analysisType
    document.getElementById('selected_video_agreement').innerHTML = videos_grouped[video_id].title
    document.getElementById('annotators').innerHTML = ""
    document.getElementById('annotator1').innerHTML = "<p class=\"titleLower\"> Select first annotator</p>"
    document.getElementById('annotator2').innerHTML = "<p class=\"titleLower\"> Select second annotator</p>"


    for (let i in annotators) {

      let radioToAdd = '<div className="form-check"> ' +

          '<label className="form-check-label" class="annotator-label" htmlFor="' + annotators[i].id + '">' +
          '<input className="form-check-input" class="annotator-radio" type="radio" name="annotator1" ' +
          'value="' + annotators[i].id + '" id="' + annotators[i].id + '">' +
          annotators[i].name +
          '</label>' +
          '</div>'

      document.getElementById('annotator1').innerHTML += radioToAdd


      radioToAdd = '<div className="form-check"> ' +

          '<label className="form-check-label" class="annotator-label" htmlFor="' + annotators[i] + '">' +
          '<input className="form-check-input" class="annotator-radio" type="radio" name="annotator2" ' +
          'value="' + annotators[i].id + '" id="' + annotators[i].id + '">' +
          annotators[i].name +
          '</label>' +
          '</div>'

      document.getElementById('annotator2').innerHTML += radioToAdd



    }

  }

  if(analysisType != "fleiss")
    next("video")
  else
    document.getElementById("analysisForm").submit();


});






function submitForm() {

    if (analysisType == "data_summary" || analysisType == "linguistic") {
      if ($("input[type='radio'][name='annotator']:checked").val() != undefined)
        document.getElementById("analysisForm").submit();
    }
    else if ($("input[type='radio'][name='annotator1']:checked").val() != undefined
          && $("input[type='radio'][name='annotator2']:checked").val() != undefined){
                document.getElementById("analysisForm").submit();
      }
  }

