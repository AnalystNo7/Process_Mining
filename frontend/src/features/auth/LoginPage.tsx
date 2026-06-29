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
          <div className="login-brand-logo" aria-hidden />
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
