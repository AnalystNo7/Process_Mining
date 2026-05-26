import { Button, Card, Checkbox, Form, Input, Typography } from 'antd';
import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

import { getErrorMessage, notifyError } from '@/lib/notify';
import { useAuthStore } from '@/stores/authStore';

interface LoginFormValues {
  username: string;
  password: string;
  use_ldap: boolean;
}

export function LoginPage() {
  const login = useAuthStore((s) => s.login);
  const navigate = useNavigate();
  const location = useLocation();
  const [loading, setLoading] = useState(false);

  const from = (location.state as { from?: string } | null)?.from ?? '/projects';

  const onFinish = async (values: LoginFormValues) => {
    setLoading(true);
    try {
      await login(values.username, values.password, values.use_ldap);
      navigate(from, { replace: true });
    } catch (error) {
      notifyError(getErrorMessage(error, 'Неверный логин или пароль'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        display: 'flex',
        minHeight: '100vh',
        alignItems: 'center',
        justifyContent: 'center',
        background:
          'linear-gradient(135deg, var(--gpc-blue-900) 0%, var(--gpc-blue) 65%, var(--gpc-blue-700) 100%)',
        padding: 24,
      }}
    >
      <Card className="card" style={{ width: 380 }} styles={{ body: { padding: 28 } }}>
        <div style={{ textAlign: 'center', marginBottom: 18 }}>
          <div
            style={{
              width: 48,
              height: 48,
              borderRadius: 12,
              background: 'var(--gpc-sky)',
              display: 'grid',
              placeItems: 'center',
              margin: '0 auto 12px',
              color: 'var(--gpc-blue-800)',
            }}
            aria-hidden
          >
            <svg viewBox="0 0 24 24" width="26" height="26" fill="currentColor">
              <path d="M12 2 3 7v10l9 5 9-5V7l-9-5Zm0 2.3 6.8 3.78L12 11.85 5.2 8.08 12 4.3ZM5 9.7l6.25 3.47v6.96L5 16.66V9.7Zm14 0v6.96l-6.25 3.47v-6.96L19 9.7Z" />
            </svg>
          </div>
          <Typography.Title level={3} style={{ margin: 0, fontFamily: 'var(--font-head)' }}>
            Process Mining
          </Typography.Title>
          <Typography.Text type="secondary" style={{ fontSize: 13 }}>
            Аналитика бизнес-процессов
          </Typography.Text>
        </div>
        <Form<LoginFormValues>
          layout="vertical"
          onFinish={onFinish}
          initialValues={{ use_ldap: false }}
        >
          <Form.Item
            name="username"
            label="Логин"
            rules={[{ required: true, message: 'Введите логин' }]}
          >
            <Input autoFocus autoComplete="username" />
          </Form.Item>
          <Form.Item
            name="password"
            label="Пароль"
            rules={[{ required: true, message: 'Введите пароль' }]}
          >
            <Input.Password autoComplete="current-password" />
          </Form.Item>
          <Form.Item name="use_ldap" valuePropName="checked">
            <Checkbox>Войти через LDAP/AD</Checkbox>
          </Form.Item>
          <Button type="primary" htmlType="submit" block loading={loading}>
            Войти
          </Button>
        </Form>
      </Card>
    </div>
  );
}
