export default function DirectorsTable({ directors }) {

    return (
        <div className="card">

            <h2>Dirigeants</h2>

            <table>

                <thead>
                    <tr>
                        <th>Nom</th>
                        <th>Prénom</th>
                        <th>Fonction</th>
                        <th>Depuis</th>
                    </tr>
                </thead>

                <tbody>

                    {directors.map((d, i) => (
                        <tr key={i}>
                            <td>{d.Nom}</td>
                            <td>{d.Prenom}</td>
                            <td>{d.Fonction}</td>
                            <td>{d.Depuis}</td>
                        </tr>
                    ))}

                </tbody>

            </table>

        </div>
    );
}