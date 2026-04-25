import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { completeMicrosoftCallback } from '../../api/microsoftApi';
import Card from '../../components/common/Card';

export default function MicrosoftCallbackPage() {
  const navigate = useNavigate();
  const [message, setMessage] = useState('Conectando cuenta Microsoft...');

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get('code');
    const state = params.get('state');
    const error = params.get('error');

    const complete = async () => {
      try {
        const response = await completeMicrosoftCallback({ code, state, error });
        setMessage(response.message || 'Cuenta conectada correctamente');

        setTimeout(() => {
          navigate('/usuario');
        }, 1200);
      } catch (err) {
        setMessage(
          err?.response?.data?.detail ||
            'No se pudo completar la vinculación con Microsoft.'
        );

        setTimeout(() => {
          navigate('/usuario');
        }, 1800);
      }
    };

    complete();
  }, [navigate]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-brand-cream p-6">
      <div className="w-full max-w-lg">
        <Card title="Microsoft OAuth" subtitle="Procesando vinculación de cuenta">
          <p className="rounded-2xl bg-brand-cream px-4 py-4 text-sm text-brand-blueDark">
            {message}
          </p>
        </Card>
      </div>
    </div>
  );
}