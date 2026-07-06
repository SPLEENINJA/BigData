export default function SearchBar({
    enterprise,
    setEnterprise,
    onSearch,
    onScrape
}) {

    return (

        <div className="search">

            <input
                value={enterprise}
                onChange={(e) => setEnterprise(e.target.value)}
                placeholder="Nom ou numéro BCE..."
            />

            <button onClick={onSearch}>
                Rechercher
            </button>

        </div>

    );

}