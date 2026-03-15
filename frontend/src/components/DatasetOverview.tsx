import type { DatasetProfile } from "../api/client";

interface Props {
  profile: DatasetProfile;
}

export default function DatasetOverview({ profile }: Props) {
  return (
    <section className="dataset-overview">
      <h2>Dataset Overview</h2>
      <p>
        <strong>{profile.row_count.toLocaleString()}</strong> rows ×{" "}
        <strong>{profile.column_count}</strong> columns
      </p>
      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Column</th>
              <th>Type</th>
              <th>Unique</th>
              <th>Missing %</th>
              <th>Sample Values</th>
            </tr>
          </thead>
          <tbody>
            {profile.columns.map((col) => (
              <tr key={col.name}>
                <td className="col-name">{col.name}</td>
                <td>
                  <span className="badge">{col.dtype}</span>
                </td>
                <td>{col.unique_count}</td>
                <td>{col.missing_pct}%</td>
                <td className="samples">
                  {col.sample_values.slice(0, 3).join(", ")}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
