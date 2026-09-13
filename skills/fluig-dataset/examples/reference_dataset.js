/**
 * Dataset: ds_exemplo_referencia
 * Projeto: <nome do projeto>
 * Versão: 1.0
 *
 * Descrição:
 * Dataset de referência seguindo todos os padrões da skill fluig-expert.
 * Demonstra extração de constraints, chamada de dataset interno e tratamento de erros.
 *
 * Constraints esperadas:
 * - colleagueId: ID do usuário (Opcional)
 */
function createDataset(fields, constraints, sortFields) {
    var dataset = DatasetBuilder.newDataset();
    dataset.addColumn("colleagueId");
    dataset.addColumn("colleagueName");
    dataset.addColumn("status");

    var colleagueId = "";

    // Padrão de extração de constraints (ECMA 5)
    if (constraints != null) {
        for (var i = 0; i < constraints.length; i++) {
            if (constraints[i].fieldName == "colleagueId") {
                colleagueId = constraints[i].initialValue;
            }
        }
    }

    try {
        var ct = [];
        if (colleagueId != "") {
            ct.push(DatasetFactory.createConstraint("colleaguePK.colleagueId", colleagueId, colleagueId, ConstraintType.MUST));
        }
        
        // Chamada de dataset interno
        var dsColleague = DatasetFactory.getDataset("colleague", null, ct, null);

        for (var j = 0; j < dsColleague.rowsCount; j++) {
            dataset.addRow(new Array(
                dsColleague.getValue(j, "colleaguePK.colleagueId"),
                dsColleague.getValue(j, "colleagueName"),
                "Ativo"
            ));
        }
    } catch (e) {
        return exibeErro("Erro ao consultar colega", e.message);
    }

    return dataset;
}

function exibeErro(msg, detalhes) {
    if (detalhes == null || detalhes == '') msg = "Erro desconhecido, verifique o log do servidor.";
    log.error('uf-log | msg: ' + msg);
    log.error('uf-log | detalhes: ' + detalhes);
    var ds = DatasetBuilder.newDataset();
    ds.addColumn("ERRO");
    ds.addColumn("MSG");
    ds.addColumn("DETALHES");
    ds.addRow(new Array("1", msg, detalhes));
    return ds;
}
