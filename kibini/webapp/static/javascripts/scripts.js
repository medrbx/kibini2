
$(document).ready(function(){$(".alert").addClass("in").fadeOut(4500);

/* swap open/close side menu icons */
$('[data-toggle=collapse]').click(function(){
  	// toggle icon
  	$(this).find("i").toggleClass("glyphicon-chevron-right glyphicon-chevron-down");
});
});

/* Ajuste la hauteur d'un iframe de tableau de bord sur celle de son contenu réel
   (même origine : /static/data/*.html, servi par cette même appli Flask).
   En cas d'échec (contenu pas encore chargé, structure inattendue...), la
   hauteur définie dans webapp/dashboards.py reste affichée telle quelle. */
function autoResizeIframe(iframe) {
    try {
        var doc = iframe.contentWindow.document;
        var height = Math.max(doc.documentElement.scrollHeight, doc.body.scrollHeight);
        if (height) {
            iframe.style.height = height + "px";
        }
    } catch (e) {
        // contenu cross-origin ou non accessible : on garde la hauteur par défaut
    }
}