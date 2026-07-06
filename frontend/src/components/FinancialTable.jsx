export default function FinancialTable({ exercices }) {

    if (!exercices) return null;

    const labels = {

        chiffre_affaires: "Chiffre d'affaires",
        achats: "Achats",
        variation_stocks: "Variation des stocks",
        ebit: "EBIT",
        resultat_net: "Résultat net",
        fonds_propres: "Fonds propres",
        capital_souscrit: "Capital souscrit",
        tresorerie: "Trésorerie",
        dettes_financieres: "Dettes financières",
        marge_brute: "Marge brute",
        marge_nette: "Marge nette",
        roe: "ROE",
        ratio_liquidite: "Ratio de liquidité",
        taux_endettement: "Taux d'endettement"

    };

    const years = Object.keys(exercices).sort();

    const metrics = Object.keys(exercices[years[0]]);
    function formatValue(v) {

    if (typeof v !== "number") return v;

    return v.toLocaleString("fr-BE", {
        maximumFractionDigits: 2
    });

}

    return (

        <div className="card">

            <h2>Historique financier</h2>

            <table>

                <thead>

                    <tr>

                        <th>Indicateur</th>

                        {years.map(year => (
                            <th key={year}>{year}</th>
                        ))}

                    </tr>

                </thead>

                <tbody>

                    {metrics.map(metric => (

                        <tr key={metric}>

                            <td>{labels[metric] ?? metric}</td>

                            {years.map(year => (

                                <td key={year}>
                                    {formatValue(exercices[year][metric])}
                                </td>

                            ))}

                        </tr>

                    ))}

                </tbody>

            </table>

        </div>

    );

}