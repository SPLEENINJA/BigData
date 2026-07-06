import { useState } from "react";
import api from "./api";

import SearchBar from "./components/SearchBar";
import FinancialTable from "./components/FinancialTable";
import DirectorsTable from "./components/DirectorsTable";
import SankeyChart from "./components/SankeyChart";
import "./app.css";

export default function App() {
function formatMoney(value) {

    if (value == null) return "-";

    const abs = Math.abs(value);

    if (abs >= 1e9)
        return `${(value / 1e9).toFixed(2)} Md`;

    if (abs >= 1e6)
        return `${(value / 1e6).toFixed(2)} M`;

    if (abs >= 1e3)
        return `${(value / 1e3).toFixed(2)} k`;

    return value.toLocaleString("fr-BE", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

function formatPercent(value) {

    if (value == null) return "-";

    return `${Number(value).toFixed(1)} %`;

}
    const [enterprise, setEnterprise] = useState("");
    const [company, setCompany] = useState(null);
    const [loading, setLoading] = useState(false);
    const [loadingDirectors, setLoadingDirectors] = useState(false);
    const [polling, setPolling] = useState(null);

    // ✅ NEW : année sélectionnée pour le Sankey
    const [selectedYear, setSelectedYear] = useState(null);

    async function fetchCompany() {

        if (!enterprise) return;

        setLoading(true);

        try {

            const res = await api.get(`/enterprise/${enterprise}`);
            const data = res.data.gold;

            setCompany(data);

            const years = Object.keys(data.exercices || {});
            setSelectedYear(years.sort().at(-1));

            // dirigeants déjà présents ?
            if (data.Directors && data.Directors.length > 0) {

                setLoadingDirectors(false);

                if (polling) {
                    clearInterval(polling);
                    setPolling(null);
                }

            } else {

                await startDirectorScraping();

            }

        } catch (err) {

            console.error(err);

            setCompany(null);

        } finally {

            setLoading(false);

    }
    async function startDirectorScraping() {

        setLoadingDirectors(true);

        await api.post(`/enterprise/${enterprise}/directors/scrape`);

        const interval = setInterval(async () => {

            try {

                const res = await api.get(`/enterprise/${enterprise}`);

                if (
                    res.data.gold.Directors &&
                    res.data.gold.Directors.length > 0
                ) {

                    setCompany(res.data.gold);

                    setLoadingDirectors(false);

                    clearInterval(interval);

                    setPolling(null);

                }

            } catch (e) {

                console.log(e);

            }

        }, 1000);

        setPolling(interval);

    }

    }
    async function scrapeDirectors() {

        if (!enterprise) return;

        try {
            await api.post(`/enterprise/${enterprise}/directors/scrape`);
            await fetchCompany();
        } catch (err) {
            console.error("SCRAPE ERROR:", err);
        }
    }

    const years = company?.exercices ? Object.keys(company.exercices).sort() : [];
    const exercice = selectedYear ? company?.exercices?.[selectedYear] : null;

    return (

        <div className="container">

            <h1 className="title">Dashboard</h1>

            <SearchBar
                enterprise={enterprise}
                setEnterprise={setEnterprise}
                onSearch={fetchCompany}
            />

            {loading && (
                <div className="card">
                    Chargement...
                </div>
            )}

            {company && !loading && (

                <>
                    {/* HEADER */}
                    <div className="company-header">

                        <h2>{company.name || "Nom indisponible"}</h2>

                        <p>BCE : {company.enterprise_number}</p>

                        <a
                            className="bce-link"
                            href={`https://kbopub.economie.fgov.be/kbopub/toonondernemingps.html?lang=fr&ondernemingsnummer=${company.enterprise_number}`}
                            target="_blank"
                            rel="noopener noreferrer"
                        >
                            ↗ Redirection BCE
                        </a>

                    </div>

                    {/* KPI */}
                    <div className="kpi-row">

                    <div className="kpi">
                        <div className="kpi-label">Chiffre d'affaires</div>
                        <div className="kpi-value">
                            {formatMoney(company.exercices?.[selectedYear]?.chiffre_affaires)}
                        </div>
                    </div>

                    <div className="kpi">
                        <div className="kpi-label">Résultat net</div>
                        <div className="kpi-value">
                            {formatMoney(company.exercices?.[selectedYear]?.resultat_net)}
                        </div>
                    </div>

                    <div className="kpi">
                        <div className="kpi-label">ROE</div>
                        <div className="kpi-value">
                            {formatPercent(company.exercices?.[selectedYear]?.roe)}
                        </div>
                    </div>

                </div>

                    {/* GRID */}
                    <div className="grid">

                        {/* LEFT */}
                        <div className="card">
                            <h2>Dirigeants</h2>

                            {loadingDirectors ? (

                                <div
                                    style={{
                                        padding: 40,
                                        textAlign: "center",
                                        fontWeight: 600,
                                        color: "#666"
                                    }}
                                >
                                    Dirigeants en cours de recherche...
                                </div>

                            ) : (

                                <DirectorsTable
                                    directors={company.Directors || []}
                                />

                            )}
                        </div>

                        {/* RIGHT - SANKey CONTROL */}
                        <div className="card">

                            <h2>Flux financier (Sankey)</h2>

                            {/* 🔥 SELECTEUR D'ANNÉE */}
                            <div className="year-selector">
                                {years.map(year => (
                                    <button
                                        key={year}
                                        className={year === selectedYear ? "active" : ""}
                                        onClick={() => setSelectedYear(year)}
                                    >
                                        {year}
                                    </button>
                                ))}
                            </div>

                            <SankeyChart
                                exercice={company.exercices?.[selectedYear]}
                                year={selectedYear}
                            />

                        </div>

                    </div>

                    {/* TABLE FULL WIDTH */}
                    <FinancialTable exercices={company.exercices} />

                </>
            )}

        </div>
    );
}