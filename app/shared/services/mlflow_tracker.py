from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, ContextManager
import mlflow
from contextlib import contextmanager


class MLflowTracker(ABC):
    """MLflow 추적 서비스 인터페이스"""

    @abstractmethod
    def start_run(self, run_name: Optional[str] = None) -> ContextManager:
        """MLflow run 시작"""
        pass

    @abstractmethod
    async def log_param(self, key: str, value: Any):
        """파라미터 로깅"""
        pass

    @abstractmethod
    async def log_params(self, params: Dict[str, Any]):
        """여러 파라미터 로깅"""
        pass

    @abstractmethod
    async def log_metric(self, key: str, value: float, step: Optional[int] = None):
        """메트릭 로깅"""
        pass

    @abstractmethod
    async def log_metrics(self, metrics: Dict[str, float], step: Optional[int] = None):
        """여러 메트릭 로깅"""
        pass

    @abstractmethod
    async def log_text(self, text: str, artifact_file: str):
        """텍스트 아티팩트 로깅"""
        pass


class StandardMLflowTracker(MLflowTracker):
    """표준 MLflow 추적 서비스"""

    def __init__(self, tracking_uri: str, experiment_name: str):
        mlflow.set_tracking_uri(tracking_uri)

        try:
            experiment = mlflow.get_experiment_by_name(experiment_name)
            if experiment is None:
                mlflow.create_experiment(experiment_name)
            mlflow.set_experiment(experiment_name)
        except Exception as e:
            print(f"MLflow 실험 설정 중 오류: {e}")

    @contextmanager
    def start_run(self, run_name: Optional[str] = None):
        """MLflow run 시작"""
        active_run = mlflow.active_run()
        # FastAPI는 단일 이벤트 루프에서 여러 요청을 처리하므로
        # 기존 run이 열려 있으면 중첩 실행으로 전환한다.
        if active_run:
            with mlflow.start_run(run_name=run_name, nested=True):
                yield
        else:
            with mlflow.start_run(run_name=run_name):
                yield

    async def log_param(self, key: str, value: Any):
        """파라미터 로깅"""
        mlflow.log_param(key, value)

    async def log_params(self, params: Dict[str, Any]):
        """여러 파라미터 로깅"""
        mlflow.log_params(params)

    async def log_metric(self, key: str, value: float, step: Optional[int] = None):
        """메트릭 로깅"""
        mlflow.log_metric(key, value, step=step)

    async def log_metrics(self, metrics: Dict[str, float], step: Optional[int] = None):
        """여러 메트릭 로깅"""
        mlflow.log_metrics(metrics, step=step)

    async def log_text(self, text: str, artifact_file: str):
        """텍스트 아티팩트 로깅"""
        mlflow.log_text(text, artifact_file)
