//Recupera informações do usuário sincronizados dataset ds_funcionariosAtivos_rest pelo e-mail
const getDadosColigada = (codColigada) => {

    var constraints = new Array();
    var dataset = null;
    var coligada = {};

    constraints.push(DatasetFactory.createConstraint("CODCOLIGADA", codColigada, codColigada, ConstraintType.MUST));
    dataset = DatasetFactory.getDataset("ds_empresaSync", null, constraints, null);

    if (dataset.values.length > 0) {

        coligada = dataset.values[0]

    }

    return coligada;

}

// Recupera informações do usuário sincronizados dataset
// ds_funcionariosAtivos_rest pelo e-mail
const getDadosFunc = (email) => {

    var constraints = new Array();
    var dataset = null;
    var user = {};

    constraints.push(DatasetFactory.createConstraint("EMAIL", email, email, ConstraintType.MUST));
    dataset = DatasetFactory.getDataset("ds_funcionariosAtivos", null, constraints, null);

    if (dataset.values.length > 0) {

        user = dataset.values[0]

    }

    return user;

}

// Recupera informações do usuário cadastrado no FLUIG pelo e-mail
const getUserByMail = (mail) => {
    var constraints = new Array();
    var dataset = null;
    var user = { "colleagueName": "", "colleagueId": "", "login": "" };

    constraints.push(DatasetFactory.createConstraint("mail", mail, mail, ConstraintType.MUST));
    constraints.push(DatasetFactory.createConstraint("active", true, true, ConstraintType.MUST));
    dataset = DatasetFactory.getDataset("colleague", null, constraints, null);

    if (dataset.values.length > 0) {
        user.colleagueId = dataset.values[0]["colleaguePK.colleagueId"];
        user.colleagueName = dataset.values[0]["colleagueName"];
        user.login = dataset.values[0]["login"];
        user.mail = dataset.values[0]["mail"];
    }

    return user;
};

// Desabilitar campos/DIV
const disablefield = (idDivs) => {
    $(idDivs).find(':input').prop('readonly', true);
    $(idDivs).find('select').css('touch-action', 'none').css('pointer-events', 'none').css('background', '#eee');
    $(idDivs).on("click", function () {
        return false;
    });
    $(idDivs).find('.btn').prop('disabled', 'disabled');
}

// Habilitar campos/DIV
const enablefield = (idDivs) => {
    $(idDivs).find(':input').prop('readonly', false);
    $(idDivs).find('select').css('touch-action', '').css('pointer-events', '').css('background', '');
    $(idDivs).off("click");
    $(idDivs).find('.btn').prop('disabled', false);
}

// Esconder Div
const hidediv = (idDivs) => {

    $(idDivs).css('display', 'none');

}


//Mostrar Div
const showdiv = (idDivs) => {

    $(idDivs).css('display', '');

}


// verifica campos fazio pelo name
const campoVazio = (fieldname) => {
    if ($("[name='" + fieldname + "']").val() == null ||
        $("[name='" + fieldname + "']").val() == undefined ||
        $("[name='" + fieldname + "']").val() == "") return true
    else return false
}

// Exibir msg de erro
const exibirMsgErroForm = (mensagem) => {
    FLUIGC.modal({
        title: 'Campos Obrigatórios',
        content:
            "<div class='alert alert-warning' role='alert'>" +
            "<strong>Atenção:</strong> " + mensagem +
            "</div>",
        id: 'modalValidation',
        size: 'large'
    })
}

const asteriscosObrigatorios = (classeBusca = 'obrigatorio') => {

    const obrigatorios = $(`.${classeBusca}:visible`);

    obrigatorios.each(function () {
        const campo = $(this).closest('div[class^="col-sm-"]').find('input, textarea, select');

        if (!campo.prop('readonly') && !campo.prop('disabled')) {
            const conteudoAtual = $(this).html();

            // Verifica se o asterisco já foi adicionado
            if (!conteudoAtual.includes('<span class="fs-color-danger"> *</span>')) {
                $(this).html(`${conteudoAtual}<span class="fs-color-danger"> *</span>`);
            }
        }
    });
}

const verificaCampos = (campos, numState) => {

    //ajusto o painel do form
    parent.$("#informationsTab").removeClass("active")
    parent.$("#informations-tab").removeClass("active in")
    parent.$("#historicTab").removeClass("active")
    parent.$("#historic-tab").removeClass("active in")
    parent.$("#tab-attachments").removeClass("active")
    parent.$("#attachments-tab").removeClass("active in")

    parent.$("#formTab").addClass("active")
    parent.$("#form-tab").addClass("active in")

    var campos = $('.obrigatorio:visible');

    // Itera sobre cada campo fornecido
    $(campos).each(function () {
        const parent = $(this).parent();
        const campo = parent.find('input, select, textarea');
        const campoType = $(campo).attr('type');
        const campoName = $(campo).attr('name');
        const errorMessage = 'O campo <i>' + $(this).html().replace('<span class="fs-color-danger">*</span>', '').replace('<br>', '') + '</i> é de preenchimento obrigatório';

        // Verifica se o campo é do tipo radio
        if (campoType === "radio") {
            if (!$(campo).prop('disabled') && !$(`input[name="${campoName}"]:checked`).val()) {
                arrError.push(errorMessage);
                campoObrig.push(campo);
            }
        }
        // Verifica se o campo é do tipo zoom
        else if (campoType === "zoom") {
            if (!$(campo).prop('disabled') && campoName && $(`[name="${campoName}"]`).val() == '') {
                arrError.push(errorMessage);
                campoObrig.push(campo);
            }
        }
        // Verifica se o campo é um elemento select
        else if ($(campo).is('select')) {
            if (campoName && !$(`[name="${campoName}"]`).val()) {
                arrError.push(errorMessage);
                campoObrig.push(campo);
            }
        }
        // Trata outros tipos de campos
        else {
            if (campoName && ((!$(campo).val() && $(campo).hasClass('bbras-anexo')) || (!$(campo).val() && !$(campo).prop('readonly')))) {
                arrError.push(errorMessage);
                campoObrig.push(campo);
            }
        }
    });

    // Chama a função para destacar campos obrigatórios
    destacaCampObrigatorio()
}

const destacaCampObrigatorio = () => {

    // Limpa destaque de campos anteriormente destacados
    limpaDestacados();

    // Verifica se há campos obrigatórios a serem tratados
    if (campoObrig.length > 0) {

        // Itera sobre cada campo obrigatório
        campoObrig.forEach(campo => {

            const campoType = $(campo).attr('type');
            const campoName = $(campo).attr('name');

            // Tratamento para campos do tipo "radio"
            if (campoType === "radio") {

                // Destaca o campo
                $(`input[name="${campoName}"]`).closest('div[class^="card"]').css({ "background-color": "#f2c8cb", "border-color": "red" });

                // Remove destaque quando o campo é alterado
                $(`input[name="${campoName}"]`).change(function () {
                    $(this).closest('div[class^="card"]').css({ "background-color": "", "border-color": "#ced4da" });
                });

                // Tratamento para campos do tipo "zoom"
            } else if (campoType === "zoom") {

                // Destaca o campo
                $(campo).siblings("span").children(":first").children().css({ "background-color": "#f2c8cb", "border-color": "red" });

                // Remove destaque quando o campo é alterado e não está vazio
                $(`[name="${campoName}"]`).change(function () {
                    if ($(this).val()) {
                        $(this).siblings("span").children(":first").children().css({ "background-color": "white", "border-color": "#ced4da" });
                    }
                });

                // Tratamento para outros tipos de campos
            } else {

                // Destaca o campo
                $(campo).css({ "background-color": "#f2c8cb", "border-color": "red" });
                $(campo).parents('div.bootstrap-tagsinput').css({ "background-color": "#f2c8cb", "border-color": "red" });

                // Remove destaque quando o campo perde o foco e não está vazio
                //autocomplete
                $(campo).parents('div.bootstrap-tagsinput').on("click", function () {
                    $(".bootstrap-tagsinput").css({ "background-color": "", "border-color": "#ced4da" })
                });

                $(campo).blur(function () {
                    if ($(this).val()) {
                        $(this).css({ "background-color": "", "border-color": "#ced4da" });
                    }
                });
            }
        });
    }
}

const limpaDestacados = () => {

    // Seleciona todos os campos marcados como obrigatórios
    const campos = $('.obrigatorio');

    // Itera sobre cada campo obrigatório
    campos.each(function () {

        // Busca o campo correspondente (input, select ou textarea) dentro do elemento pai
        const campo = $(this).parent().find('input, select, textarea');
        const campoType = $(campo).attr('type');
        const campoName = $(campo).attr('name');

        // Tratamento para campos do tipo "radio"
        if (campoType === "radio") {

            // Remove o destaque do campo
            $(`input[name="${campoName}"]`).closest('div[class^="card"]').css({ "background-color": "" });

            // Tratamento para campos do tipo "zoom"
        } else if (campoType === "zoom") {

            // Remove o destaque do campo
            $(campo).siblings("span").children(":first").children().css({ "background-color": "white" });

            // Tratamento para outros tipos de campos
        } else {

            // Remove o destaque do campo
            $(campo).css({ "background-color": "" });

        }
    });
}

const limpaCamposDiv = (idDiv) => {

    // Limpar todos os campos de texto
    $(`#${idDiv} input[type='text']`).val("");

    // Limpar todos os campos de seleção
    $(`#${idDiv} select`).val("");

    // Limpar todos os campos de seleção
    $(`#${idDiv} textarea`).val("");

}

// Recupero a URL do ambiente logado
const fluigUrl = window.location.origin

// Criar pasta
const criarPasta = async (parentId, description, callback) => {
    const request_data_folder = {
        url: fluigUrl + '/api/public/ecm/document/createFolder',
        method: 'POST'
    }
    const dataFolder = {
        "description": description.toString(),
        "parentId": parseInt(parentId)
    }
    try {
        $.ajax({
            url: request_data_folder.url,
            crossDomain: true,
            async: true,
            type: request_data_folder.method,
            data: JSON.stringify(dataFolder),
            contentType: "application/json",
            success: (function (response) {
                const result = response.content.id
                callback(result)
            })
        })
    } catch (error) {
        console.log(error)
    }
}

const criarDocumento = async (file, idPasta, callback) => {
    const fileName = file.name
    const request_data_ecm = {
        url: fluigUrl + '/ecm/upload',
        method: 'POST'
    }
    const request_data_document = {
        url: fluigUrl + '/api/public/ecm/document/createDocument',
        method: 'POST'
    }
    const formData = new FormData()
    formData.append(fileName, file)
    $.ajax({
        async: true,
        crossDomain: true,
        url: request_data_ecm.url,
        method: request_data_ecm.method,
        processData: false,
        contentType: false,
        mimeType: "multipart/form-data",
        data: formData,
        success: ((response) => {
            const dataDocument = {
                "description": fileName,
                "parentId": idPasta,
                "downloadEnabled": true,
                "attachments": [{
                    "fileName": fileName
                }],
            }
            $.ajax({
                async: true,
                crossDomain: true,
                url: request_data_document.url,
                type: request_data_document.method,
                contentType: "application/json",
                processData: false,
                data: JSON.stringify(dataDocument),
                success: (function (response) {
                    const result = response.content.id
                    callback(result)
                })
            })
        })
    })
}

const excluirDocumento = async (documentId, callback) => {
    const request_data_folder = {
        url: fluigUrl + '/content-management/api/v2/documents/' + documentId,
        method: 'DELETE'
    }
    try {
        $.ajax({
            url: request_data_folder.url,
            crossDomain: true,
            async: true,
            type: request_data_folder.method,
            success: (function (response) {
                callback()
            })
        })
    } catch (error) {
        console.log(error)
    }
}

const verDocumento = (documentId) => {
    const urlDocument = fluigUrl + "/portal/p/1/ecmnavigation?app_ecm_navigation_doc=" + documentId
    window.open(urlDocument, "_blank")
}

const validaCnpjCpf = (campoCnpj) => {

    if ($(campoCnpj).val() && $(campoCnpj).is(':visible') && !$(campoCnpj).attr('readonly')) {
        // Verifica a validade do CNPJ
        if (!validaCNPJ($(campoCnpj).val())) {
            // Verifica a validade do CPF
            if (!validaCPF($(campoCnpj).val())) {

                arrError.push('Valor digitado para  <i>CNPJ/CPF</i> é inválido.')
                // Destaca o campo
                $(campoCnpj).css({ "background-color": "#f2c8cb" });

                // Remove destaque quando o campo perde o foco e não está vazio
                $(campoCnpj).blur(function () {
                    if ($(this).val()) {
                        $(this).css({ "background-color": "" });
                    }
                });
            }
        }
    }
}

const validaCPF = (cpf) => {

    // Garante que o cpf é uma string
    if (typeof cpf !== 'string') return false;

    // Remove espaços, pontos e traços
    cpf = cpf.replace(/[\s.-]*/igm, '');

    // Verifica se o CPF tem 11 caracteres e não está na lista de CPFs inválidos
    if (cpf.length != 11 || /^(\d)\1{10}$/.test(cpf)) {
        return false;
    }

    // Calcula o primeiro dígito verificador
    let soma = 0;
    for (let i = 1; i <= 9; i++) {
        soma += parseInt(cpf.charAt(i - 1)) * (11 - i);
    }
    let resto = (soma % 11) < 2 ? 0 : 11 - (soma % 11);
    if (resto !== parseInt(cpf.charAt(9))) {
        return false;
    }

    // Calcula o segundo dígito verificador
    soma = 0;
    for (let i = 1; i <= 10; i++) {
        soma += parseInt(cpf.charAt(i - 1)) * (12 - i);
    }
    resto = (soma % 11) < 2 ? 0 : 11 - (soma % 11);
    if (resto !== parseInt(cpf.charAt(10))) {
        return false;
    }

    return true;
}

const validaCNPJ = (cnpj) => {
    // Remove caracteres não numéricos
    cnpj = cnpj.replace(/[^0-9]/g, '');

    // Verifica o tamanho e se não é uma sequência repetida
    if (cnpj.length !== 14 || /^(\d)\1{13}$/.test(cnpj)) {
        return false;
    }

    // Função auxiliar para calcular um dígito verificador
    function calcularDigito(str, peso) {
        let soma = 0;
        for (let i = 0; i < str.length; i++) {
            soma += parseInt(str.charAt(i)) * peso[i];
        }
        let resto = soma % 11;
        return (resto < 2) ? 0 : 11 - resto;
    }

    // Peso para calcular o primeiro dígito
    let peso = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
    if (calcularDigito(cnpj.slice(0, 12), peso) !== parseInt(cnpj.charAt(12))) {
        return false;
    }

    // Peso para calcular o segundo dígito
    peso.unshift(6);
    if (calcularDigito(cnpj.slice(0, 13), peso) !== parseInt(cnpj.charAt(13))) {
        return false;
    }

    return true;
}

const alteraClasse = (idLabel, tipo) => {
    const labelElement = document.getElementById(idLabel); // Seleciona o elemento <label>

    if (tipo == 1) {
        // Adicionar a classe "obrigatorio"
        labelElement.classList.add('obrigatorio')
    } else if (tipo == 2) {
        // Remover a classe "obrigatorio"
        labelElement.classList.remove('obrigatorio');
    }
}


const currencyToNumber = (numero) => {
    if (numero != null && numero != undefined && numero != '') {
        numero = numero.split(',')
        numero[0] = numero[0].split('.').join('')
        return parseFloat(numero.join('.'))
    } else {
        return 0
    }
}
const numberToCurrency = (numero) => {
    var numero = parseFloat(numero).toFixed(2).split('.')
    numero[0] = numero[0].split(/(?=(?:...)*$)/).join('.')
    return numero.join(',')
}

/*
 * const alteraClasse = (idLabel, tipo) => { const labelElement =
 * document.getElementById(idLabel); // Seleciona o elemento <label>
 * 
 * if (tipo == 1) { // Adicionar a classe "obrigatorio"
 * labelElement.classList.add('obrigatorio') } else if (tipo == 2) { // Remover
 * a classe "obrigatorio" labelElement.classList.remove('obrigatorio'); } }
 */
