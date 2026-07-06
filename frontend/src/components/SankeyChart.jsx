import Plot from "react-plotly.js";

export default function SankeyChart({ exercice, year }) {

    if (!exercice) return null;

    const ca = Number(exercice.chiffre_affaires ?? 0);
    const achats = Math.max(Number(exercice.achats ?? 0), 0);
    const stocks = Math.max(Number(exercice.variation_stocks ?? 0), 0);

    const margeBrute = Number(
        exercice.marge_brute && exercice.marge_brute !== 0
            ? exercice.marge_brute
            : ca - achats + stocks
    );

    const ebit = Number(exercice.ebit ?? 0);
    const rn = Number(exercice.resultat_net ?? 0);

    const positive = (x) => Math.max(x, 0);
    const negative = (x) => Math.max(-x, 0);

    const labels = [
        "Chiffre d'affaires",
        "Achats",
        "Variation stocks",
        "Marge brute",
        "EBIT",
        "Résultat net",
        "Pertes d'exploitation",
        "Perte nette"
    ];

    const colors = [
        "#2563eb",
        "#ef4444",
        "#f59e0b",
        "#14b8a6",
        "#8b5cf6",
        "#10b981",
        "#dc2626",
        "#7f1d1d"
    ];

    const source = [];
    const target = [];
    const value = [];
    const linkColor = [];

    function add(s, t, v, c) {
        if (v <= 0) return;
        source.push(s);
        target.push(t);
        value.push(v);
        linkColor.push(c);
    }

    // CA -> Achats
    add(0, 1, achats, "rgba(239,68,68,.45)");

    // CA -> Marge brute
    add(0, 3, positive(margeBrute), "rgba(37,99,235,.45)");

    // Marge brute -> EBIT
    if (ebit >= 0) {
        add(3, 4, ebit, "rgba(20,184,166,.45)");
    } else {
        add(3, 6, -ebit, "rgba(220,38,38,.55)");
    }

    // EBIT -> Résultat net
    if (ebit > 0 && rn >= 0) {
        add(4, 5, rn, "rgba(16,185,129,.45)");
    }

    // Perte d'exploitation -> Perte nette
    if (ebit < 0) {
        add(6, 7, negative(rn), "rgba(127,29,29,.65)");
    }

    return (

        <div className="card sankey-card">

            <h2>Soldes intermédiaires de gestion ({year})</h2>

            <Plot
                data={[
                    {
                        type: "sankey",

                        arrangement: "snap",

                        node: {
                            pad: 22,
                            thickness: 18,
                            line: {
                                color: "white",
                                width: 1
                            },
                            label: labels,
                            color: colors
                        },

                        link: {
                            source,
                            target,
                            value,
                            color: linkColor
                        }
                    }
                ]}

                layout={{
                    autosize: true,
                    paper_bgcolor: "white",
                    plot_bgcolor: "white",
                    font: {
                        family: "Inter",
                        size: 12
                    },
                    margin: {
                        l: 10,
                        r: 10,
                        t: 10,
                        b: 10
                    }
                }}

                config={{
                    displayModeBar: false,
                    responsive: true
                }}

                style={{
                    width: "100%",
                    height: "650px"
                }}
            />

        </div>

    );

}