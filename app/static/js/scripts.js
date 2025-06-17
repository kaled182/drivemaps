// Exemplo base para static/js/scripts.js
// Use este arquivo para scripts específicos de páginas ou componentes
// que não sejam do mapa ou do funcionamento global (main.js).

// Inicialização de componentes específicos
document.addEventListener("DOMContentLoaded", function() {
    // Exemplo: manipulação de formulário de importação
    const importForm = document.getElementById("import-form");
    if (importForm) {
        importForm.addEventListener("submit", function(evt) {
            // Você pode adicionar validações ou feedbacks antes do envio
            // evt.preventDefault(); // Descomente se quiser impedir o submit padrão
            console.log("Formulário de importação enviado!");
        });
    }

    // Outros scripts específicos podem ser adicionados aqui.
    // Por exemplo, manipulação de tabelas, tooltips, etc.
});

// Funções auxiliares para uso geral nesta página
function highlightRow(rowId) {
    const row = document.getElementById(rowId);
    if (row) {
        row.classList.add("highlight");
        setTimeout(() => row.classList.remove("highlight"), 2000);
    }
}

// Exemplo de tornar a função global, se for chamada inline no HTML
window.highlightRow = highlightRow;
