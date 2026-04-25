import { useEffect, useMemo, useState } from 'react';
import DashboardLayout from "../../layouts/DashboardLayout";
import Card from "../../components/common/Card";
import Badge from "../../components/common/Badge";
import { getAdvancedStats } from "../../api/emailApi";

function StatItem({ label, value, color = 'default' }) {
  return (
    <div className="rounded-2xl border border-brand-blueSoft/15 bg-white p-4 shadow-soft">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-medium text-slate-500">{label}</p>
        <Badge color={color}>{label}</Badge>
      </div>
      <p className="mt-4 text-3xl font-bold text-brand-blueDark">{value}</p>
    </div>
  );
}

function SimpleBarList({ title, data }) {
  const entries = Object.entries(data || {});
  const maxValue = Math.max(...entries.map(([, value]) => value), 1);

  return (
    <Card title={title}>
      {entries.length === 0 ? (
        <p className="text-sm text-slate-500">No hay datos disponibles.</p>
      ) : (
        <div className="space-y-4">
          {entries.map(([key, value]) => {
            const width = `${(value / maxValue) * 100}%`;
            return (
              <div key={key} className="space-y-1">
                <div className="flex items-center justify-between gap-3">
                  <span className="truncate text-sm font-medium text-brand-blueDark">
                    {key}
                  </span>
                  <span className="text-sm font-semibold text-slate-600">{value}</span>
                </div>
                <div className="h-3 overflow-hidden rounded-full bg-brand-cream">
                  <div
                    className="h-full rounded-full bg-brand-blue"
                    style={{ width }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
}

function ConfusionMatrix({ matrix }) {
  const rows = Object.keys(matrix || {});
  const columns = Array.from(
    new Set(
      rows.flatMap((row) => Object.keys(matrix[row] || {}))
    )
  );

  if (rows.length === 0 || columns.length === 0) {
    return (
      <Card title="Matriz de confusión">
        <p className="text-sm text-slate-500">No hay datos disponibles.</p>
      </Card>
    );
  }

  const maxValue = Math.max(
    ...rows.flatMap((row) => columns.map((col) => matrix[row]?.[col] || 0)),
    1
  );

  const getOpacity = (value) => {
    const normalized = value / maxValue;
    return Math.max(0.08, normalized);
  };

  return (
    <Card
      title="Matriz de confusión"
      subtitle="Compara categoría original vs categoría final"
    >
      <div className="overflow-x-auto">
        <table className="min-w-full border-separate border-spacing-2">
          <thead>
            <tr>
              <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                Original \ Final
              </th>
              {columns.map((col) => (
                <th
                  key={col}
                  className="px-3 py-2 text-center text-xs font-semibold uppercase tracking-wide text-slate-500"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row}>
                <td className="rounded-xl bg-brand-cream px-3 py-2 text-sm font-semibold text-brand-blueDark">
                  {row}
                </td>
                {columns.map((col) => {
                  const value = matrix[row]?.[col] || 0;
                  return (
                    <td
                      key={`${row}-${col}`}
                      className="rounded-xl px-3 py-4 text-center text-sm font-bold text-brand-blueDark"
                      style={{
                        backgroundColor: `rgba(53, 93, 110, ${getOpacity(value)})`,
                      }}
                    >
                      {value}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

export default function AdminDashboardPage() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const loadStats = async () => {
      try {
        setLoading(true);
        setError('');
        const data = await getAdvancedStats();
        setStats(data);
      } catch (err) {
        console.error(err);
        setError('No se pudieron cargar las métricas administrativas.');
      } finally {
        setLoading(false);
      }
    };

    loadStats();
  }, []);

  const lowConfidencePercent = useMemo(() => {
    if (!stats?.total_emails) return 0;
    return ((stats.low_confidence_count / stats.total_emails) * 100).toFixed(1);
  }, [stats]);

  const manualCorrectionPercent = useMemo(() => {
    if (!stats?.total_emails) return 0;
    return ((stats.manual_corrections / stats.total_emails) * 100).toFixed(1);
  }, [stats]);

  return (
    <DashboardLayout
      title="Panel administrativo"
      subtitle="Métricas globales del sistema de clasificación de correos"
    >
      {loading ? (
        <Card title="Cargando panel">
          <p className="text-sm text-slate-500">Estamos consultando las métricas del sistema...</p>
        </Card>
      ) : error ? (
        <Card title="Error al cargar" className="border-brand-red/20">
          <p className="text-sm text-brand-red">{error}</p>
        </Card>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <StatItem
              label="Total correos"
              value={stats?.total_emails ?? 0}
              color="blue"
            />
            <StatItem
              label="Confianza promedio"
              value={stats?.average_confidence ?? 0}
              color="green"
            />
            <StatItem
              label="Baja confianza"
              value={stats?.low_confidence_count ?? 0}
              color="amber"
            />
            <StatItem
              label="Correcciones"
              value={stats?.manual_corrections ?? 0}
              color="red"
            />
          </div>

          <div className="grid gap-6 xl:grid-cols-2">
            <Card title="Resumen del sistema">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="rounded-2xl bg-brand-cream p-4">
                  <p className="text-sm font-medium text-slate-500">
                    Porcentaje de baja confianza
                  </p>
                  <p className="mt-2 text-2xl font-bold text-brand-blueDark">
                    {lowConfidencePercent}%
                  </p>
                </div>

                <div className="rounded-2xl bg-brand-cream p-4">
                  <p className="text-sm font-medium text-slate-500">
                    Porcentaje de corrección manual
                  </p>
                  <p className="mt-2 text-2xl font-bold text-brand-blueDark">
                    {manualCorrectionPercent}%
                  </p>
                </div>
              </div>
            </Card>

            <SimpleBarList
              title="Correos por categoría"
              data={stats?.by_category || {}}
            />
          </div>

          <div className="grid gap-6 xl:grid-cols-2">
            <SimpleBarList
              title="Correos por cuenta Microsoft"
              data={stats?.by_account || {}}
            />

            <SimpleBarList
              title="Correos por usuario"
              data={stats?.by_user || {}}
            />
          </div>

          <ConfusionMatrix matrix={stats?.confusion_matrix || {}} />
        </>
      )}
    </DashboardLayout>
  );
}