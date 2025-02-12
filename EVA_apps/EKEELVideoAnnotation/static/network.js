function downloadObjectAsJson(exportObj, exportName){
    var dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(exportObj,null,2));
    var downloadAnchorNode = document.createElement('a');
    downloadAnchorNode.setAttribute("href",     dataStr);
    downloadAnchorNode.setAttribute("download", exportName + ".json");
    document.body.appendChild(downloadAnchorNode); // required for firefox
    downloadAnchorNode.click();
    downloadAnchorNode.remove();
}

function downloadTranscript(){
    sentences = []
    $(".sentence-marker").each(function(_, sentenceElem) {
    	let sentence = {    
            "start_time":parseFloat(sentenceElem.getAttribute("data-start")),
    		"end_time":parseFloat(sentenceElem.getAttribute("data-end")),
    		"sentence":sentenceElem.innerText.split(": ").splice(-1)[0],
    		"words": []
        }
    	$(sentenceElem).find("span").each(function(_, lemmaElem) {
    		let word = {
    			"word": lemmaElem.innerText,
                "lemma": lemmaElem.getAttribute("lemma"),
    			"start_time": parseFloat(lemmaElem.getAttribute("start_time")),
    			"end_time": parseFloat(lemmaElem.getAttribute("end_time")),
    			"cpos": lemmaElem.getAttribute("cpos"),
    			"pos": lemmaElem.getAttribute("pos"),
    			"gen": lemmaElem.getAttribute("gen"),
    			"num": lemmaElem.getAttribute("num"),
                "part_of_concepts": lemmaElem.classList.contains("concept") ? lemmaElem.getAttribute("concept").trim() : ""
            }
    		sentence.words.push(word);
    	})
    	sentences.push(sentence)
    })

    downloadObjectAsJson({  "_comment": `Transcript generated using ${$isTempTranscript ? 'Google Transcript API' : 'Whisper Model large-v3'}. For pos references http://www.italianlp.it/docs/ISST-TANL-POStagset.pdf`,
                            "video_id": $video_id, 
                            "language":$language,
                            "transcript":sentences }, "transcript")
}

function downloadManuGraphAsJson(){

    //console.log("***** EKEEL - Video Annotation: create_graph.js::downloadManuGraphAsJson(): Inizio *****")

    let annotations = {
        "id": $video_id,
        "relations":relations,
        "definitions": definitions,
        "annotator": $annotator,
        "conceptVocabulary": $conceptVocabulary,
        "language": $language,
    }

    var js_data = JSON.stringify(annotations);

    $.ajax({
        url: '/annotator/download_graph',
        type : 'post',
        contentType: 'application/json',
        dataType : 'json',
        data : js_data
    }).done(function(result) {
        //console.log(result)
        downloadObjectAsJson(result, "graph");
    })    
}

function uploadManuGraphOnDB(){

    let annotations = {
        "id": $video_id,
        "relations":relations,
        "definitions": definitions,
        "annotator": $annotator,
        "conceptVocabulary": $conceptVocabulary,
        "language": $language,
        "is_completed": isCompleted
    }
    //savedText = document.getElementById("saveGraphText")
    //savedText.style.display = "block"
    //console.log("uploadGraphOnDB")

    var js_data = JSON.stringify(annotations);

    $.ajax({
        url: '/annotator/upload_graph',
        type : 'post',
        contentType: 'application/json',
        dataType : 'json',
        data : js_data
    }).done(function(result) {
        console.log(result)
        if(result.done == false) {
            alert("Error in saving graph!")
        }
        //if(result.done == true) {
        //    savedText.textContent = "Saved graph successfully!"
        //    savedText.style.color = "green";
        //    savedText.style.display = "block";
        //    setTimeout(function() { 
        //        savedText.textContent = "Saving graph...";
        //        savedText.style.color = "black";
        //        savedText.style.display = "none";
        //
        //    } ,2000)
        //}
    })
}