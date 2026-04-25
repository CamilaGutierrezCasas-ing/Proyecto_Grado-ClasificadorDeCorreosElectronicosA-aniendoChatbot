import { useEffect, useMemo, useState } from 'react';
import {
  getMicrosoftAccounts,
  getMicrosoftConnectUrl,
  disconnectMicrosoftAccount,
} from '../../api/microsoftApi';
import DashboardLayout from '../../layouts/DashboardLayout';
import ConnectedAccounts from '../../components/dashboard/ConnectedAccounts';
import EmailTable from '../../components/dashboard/EmailTable';
import StatCard from '../../components/common/StatCard';
import {
  getMyEmails,
  getEmailsByCategory,
  syncEmails,
} from '../../api/emailApi';
import EmailCategoriesSidebar from '../../components/dashboard/EmailCategoriesSidebar';
import EmailDetailModal from '../../components/dashboard/EmailDetailModal';
import ChatbotWidget from '../../components/dashboard/ChatbotWidget';
import { useAuth } from '../../hooks/useAuth';

export default function UserDashboardPage() {
  const { user } = useAuth();
  const [accounts, setAccounts] = useState([]);
  const [emails, setEmails] = useState([]);
  const [loadingAccounts, setLoadingAccounts] = useState(true);
  const [loadingEmails, setLoadingEmails] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState('todos');
  const [selectedEmail, setSelectedEmail] = useState(null);

  const loadAccounts = async () => {
    setLoadingAccounts(true);
    try {
      const data = await getMicrosoftAccounts();
      setAccounts(data);
    } finally {
      setLoadingAccounts(false);
    }
  };

  const loadEmails = async () => {
    setLoadingEmails(true);
    try {
      const data = await getMyEmails();
      setEmails(data);
    } finally {
      setLoadingEmails(false);
    }
  };

  useEffect(() => {
    loadAccounts();
    loadEmails();
  }, []);

  const handleConnect = async () => {
    const data = await getMicrosoftConnectUrl();
    window.location.href = data.authorization_url;
  };

  const handleDisconnect = async (accountId) => {
    await disconnectMicrosoftAccount(accountId);
    await loadAccounts();
  };

  const handleSync = async (accountId) => {
    await syncEmails(accountId);
    await loadEmails();
  };

  const handleCategoryFilter = async (category) => {
    setSelectedCategory(category);
    setLoadingEmails(true);
    try {
      const data =
        category === 'todos'
          ? await getMyEmails()
          : await getEmailsByCategory(category);
      setEmails(data);
    } finally {
      setLoadingEmails(false);
    }
  };

  const handleEmailUpdated = (updatedEmail) => {
    setEmails((prev) =>
      prev.map((item) => (item.id === updatedEmail.id ? updatedEmail : item))
    );
    setSelectedEmail(updatedEmail);
  };

  const stats = useMemo(() => {
    return {
      connectedAccounts: accounts.filter((item) => item.is_active).length,
      processedEmails: emails.length,
    };
  }, [accounts, emails]);

  return (
    <DashboardLayout
      title={`Bienvenida, ${user?.name || 'usuario'}`}
      subtitle="Gestiona tus cuentas, revisa tus correos y organiza tu bandeja inteligente."
    >
      <section className="grid gap-4 md:grid-cols-2">
        <StatCard
          label="Cuentas activas"
          value={stats.connectedAccounts}
          hint="Cuentas Microsoft vinculadas"
        />
        <StatCard
          label="Correos procesados"
          value={stats.processedEmails}
          hint="Correos almacenados en tu historial"
        />
      </section>

      <ConnectedAccounts
        accounts={accounts}
        onConnect={handleConnect}
        onSync={handleSync}
        onDisconnect={handleDisconnect}
        loading={loadingAccounts}
      />

      <div className="grid gap-6 lg:grid-cols-[220px_1fr]">
        <EmailCategoriesSidebar
          selected={selectedCategory}
          onSelect={handleCategoryFilter}
        />

        {loadingEmails ? (
          <p className="text-sm text-slate-500">Cargando correos...</p>
        ) : (
          <EmailTable emails={emails} onViewDetail={setSelectedEmail} />
        )}
      </div>

      <ChatbotWidget />

      {selectedEmail && (
        <EmailDetailModal
          email={selectedEmail}
          onClose={() => setSelectedEmail(null)}
          onUpdated={handleEmailUpdated}
        />
      )}
    </DashboardLayout>
  );
}