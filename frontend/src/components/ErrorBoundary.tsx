import { Button, Result } from 'antd';
import { Component, type ErrorInfo, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error('Необработанная ошибка UI:', error, info);
  }

  render(): ReactNode {
    if (this.state.hasError) {
      return (
        <Result
          status="error"
          title="Что-то пошло не так"
          subTitle="Произошла непредвиденная ошибка интерфейса."
          extra={
            <Button type="primary" onClick={() => window.location.reload()}>
              Перезагрузить
            </Button>
          }
        />
      );
    }
    return this.props.children;
  }
}
