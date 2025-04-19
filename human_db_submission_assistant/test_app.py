import unittest
import json
import os
import tempfile
from unittest.mock import patch, MagicMock, AsyncMock, mock_open
import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

# Import the app and functions to test
from app import (
    app,
    check_similarity_of_icd10,
    query_openai,
    extract_output_from_openai,
    extract_data_from_pdf,
    get_dataset_info,
    get_research_info,
    analyze_dataset,
    suggest_icd10_code,
    create_assessment_report,
    fetch_from_doi,
    fetch_abstract_europepmc,
    ApplicationData,
    DatasetInfo,
    DatasetAnalysisResult,
    ResearchInfo,
)

# テストクライアントの作成
client = TestClient(app)


class TestHelperFunctions(unittest.TestCase):
    """Helper関数のテストクラス"""

    def test_check_similarity_of_icd10(self):
        """ICD-10コードの類似性チェック関数のテスト"""
        # 同じコード
        self.assertTrue(check_similarity_of_icd10("C50", "C50"))

        # 一方がもう一方を含む場合
        self.assertTrue(check_similarity_of_icd10("C50", "C50.1"))
        self.assertTrue(check_similarity_of_icd10("C50.1", "C50"))

        # 末尾の1文字以外が同じ場合
        self.assertTrue(check_similarity_of_icd10("C50.1", "C50.2"))

        # 全く異なるコード
        self.assertFalse(check_similarity_of_icd10("C50", "D10"))
        self.assertFalse(check_similarity_of_icd10("C50.1", "C51.1"))


@pytest.mark.asyncio
class TestOpenAIFunctions:
    """OpenAI APIを使う関数のテストクラス"""

    @patch("app.llm")
    async def test_query_openai(self, mock_llm):
        """query_openai関数のテスト"""
        # モックの戻り値を設定
        mock_response = MagicMock()
        mock_response.content = "テスト応答"
        mock_llm.invoke.return_value = mock_response

        # 関数を呼び出し
        result = await query_openai(
            "テストプロンプト", "システムメッセージ", "task_123"
        )

        # アサーション
        assert result == "テスト応答"
        mock_llm.invoke.assert_called_once()

    @patch("app.llm")
    async def test_extract_output_from_openai(self, mock_llm):
        """extract_output_from_openai関数のテスト"""

        # モック出力モデル
        class TestOutputModel(BaseModel):
            test_field: str

        # モックの戻り値を設定
        mock_llm.with_structured_output.return_value.invoke.return_value = (
            TestOutputModel(test_field="テスト出力")
        )

        # 関数を呼び出し
        result = await extract_output_from_openai(
            "テストプロンプト",
            TestOutputModel,
            system_message="システムメッセージ",
            task_id="task_123",
        )

        # アサーション
        assert isinstance(result, TestOutputModel)
        assert result.test_field == "テスト出力"
        mock_llm.with_structured_output.assert_called_once_with(TestOutputModel)

    @patch("app.llm")
    async def test_suggest_icd10_code(self, mock_llm):
        """suggest_icd10_code関数のテスト"""
        # モックの戻り値を設定
        mock_llm.with_structured_output.return_value.invoke.return_value = MagicMock(
            icd10_code="C50", title="乳房の悪性新生物"
        )

        # 関数を呼び出し
        result = await suggest_icd10_code("テストプロンプト")

        # アサーション
        assert result == "C50 乳房の悪性新生物"
        mock_llm.with_structured_output.assert_called_once()


@pytest.mark.asyncio
class TestDataProcessingFunctions:
    """データ処理関数のテストクラス"""

    @patch("app.PyPDFLoader")
    @patch("app.extract_output_from_openai")
    async def test_extract_data_from_pdf(self, mock_extract_output, mock_pdf_loader):
        """PDFからのデータ抽出関数のテスト"""
        # モックの戻り値を設定
        mock_page = MagicMock()
        mock_page.page_content = "テストPDFコンテンツ"
        mock_pdf_loader.return_value.load_and_split.return_value = [mock_page]

        mock_app_data = ApplicationData(
            application_id="APP123",
            dataset_id_list=["DS001", "DS002"],
            related_studies_published=["10.1234/test.123"],
            research_abstract="研究概要",
            research_purpose="研究目的",
        )
        mock_extract_output.return_value = mock_app_data

        # 関数を呼び出し
        result = await extract_data_from_pdf("test.pdf")

        # アサーション
        assert result == mock_app_data
        mock_pdf_loader.assert_called_once_with("test.pdf")
        mock_extract_output.assert_called_once()

    @patch("aiohttp.ClientSession.get")
    @patch("app.extract_output_from_openai")
    async def test_get_dataset_info_success(self, mock_extract_output, mock_get):
        """get_dataset_info関数の成功ケースのテスト"""
        # モックの戻り値を設定
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="<html>テストHTML</html>")
        mock_get.return_value.__aenter__.return_value = mock_response

        mock_extraction_result = MagicMock(
            human_data_url="https://humandbs.dbcls.jp/hum0001-v01"
        )
        mock_extract_output.return_value = mock_extraction_result

        # 関数を呼び出し
        result = await get_dataset_info("DS001", "task_123")

        # アサーション
        assert isinstance(result, DatasetInfo)
        assert result.research_url == "https://humandbs.dbcls.jp/hum0001-v01"
        assert result.dataset_id == "DS001"

    @patch("aiohttp.ClientSession.get")
    @patch("app.extract_output_from_openai")
    async def test_get_dataset_info_failure(self, mock_extract_output, mock_get):
        """get_dataset_info関数の失敗ケースのテスト"""
        # モックの戻り値を設定 - HTTPステータスが失敗
        mock_response = AsyncMock()
        mock_response.status = 404
        mock_get.return_value.__aenter__.return_value = mock_response

        # 関数を呼び出し
        result = await get_dataset_info("DS001", "task_123")

        # アサーション
        assert result is None
        mock_extract_output.assert_not_called()

    @patch("app.fetch_from_doi")
    @patch("app.suggest_icd10_code")
    async def test_get_research_info(self, mock_suggest_icd10, mock_fetch_from_doi):
        """get_research_info関数のテスト"""
        # モックの戻り値を設定
        mock_fetch_from_doi.return_value = {
            "title": "テスト論文",
            "authors": ["山田 太郎", "鈴木 一郎"],
            "abstract": "テスト概要",
            "url": "https://example.com/paper",
        }
        mock_suggest_icd10.return_value = "C50 乳房の悪性新生物"

        # 関数を呼び出し
        result = await get_research_info("10.1234/test.123", "task_123")

        # アサーション
        assert isinstance(result, ResearchInfo)
        assert result.title == "テスト論文"
        assert result.doi == "10.1234/test.123"
        assert result.authors == ["山田 太郎", "鈴木 一郎"]
        assert result.abstract == "テスト概要"
        assert result.url == "https://example.com/paper"
        assert result.icd10 == "C50 乳房の悪性新生物"

    @patch("aiohttp.ClientSession.get")
    async def test_fetch_from_doi_success(self, mock_get):
        """fetch_from_doi関数の成功ケースのテスト"""
        # モックの戻り値を設定
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.content_type = "application/json"
        mock_response.json = AsyncMock(
            return_value={
                "title": "テスト論文",
                "author": [
                    {"given": "太郎", "family": "山田"},
                    {"given": "一郎", "family": "鈴木"},
                ],
                "abstract": "テスト概要",
                "link": [
                    {"URL": "https://example.com/paper", "content-type": "text/html"}
                ],
            }
        )
        mock_get.return_value.__aenter__.return_value = mock_response

        # 関数を呼び出し
        result = await fetch_from_doi("10.1234/test.123")

        # アサーション
        assert result["title"] == "テスト論文"
        assert result["authors"] == ["太郎 山田", "一郎 鈴木"]
        assert result["abstract"] == "テスト概要"
        assert result["url"] == "https://example.com/paper"

    @patch("aiohttp.ClientSession.get")
    async def test_fetch_abstract_europepmc(self, mock_get):
        """fetch_abstract_europepmc関数のテスト"""
        # モックの戻り値を設定
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "resultList": {
                    "result": [{"abstractText": "テスト概要 from EuropePMC"}]
                }
            }
        )
        mock_get.return_value.__aenter__.return_value = mock_response

        # 関数を呼び出し
        result = await fetch_abstract_europepmc("10.1234/test.123")

        # アサーション
        assert result == "テスト概要 from EuropePMC"

    @patch("aiohttp.ClientSession.get")
    @patch("app.extract_output_from_openai")
    async def test_analyze_dataset(self, mock_extract_output, mock_get):
        """analyze_dataset関数のテスト"""
        # モックの戻り値を設定
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(
            return_value="<html><body>テストコンテンツ</body></html>"
        )
        mock_get.return_value.__aenter__.return_value = mock_response

        # 抽出結果のモック
        class DataSetSummary(BaseModel):
            id: str
            description: str
            icd10_code: str

        class ExtractionResult(BaseModel):
            dataset_summaries: list
            analysis_method: str

        class Simirarity(BaseModel):
            analysis_method_similarity: str
            analysis_method_similarity_reason: str

        mock_extraction_result = ExtractionResult(
            dataset_summaries=[
                DataSetSummary(id="DS001", description="テスト説明", icd10_code="C50")
            ],
            analysis_method="テスト解析方法",
        )

        mock_similarity = Simirarity(
            analysis_method_similarity="高", analysis_method_similarity_reason="理由"
        )

        mock_extract_output.side_effect = [mock_extraction_result, mock_similarity]

        # 関数を呼び出し
        result = await analyze_dataset(
            "https://example.com/dataset",
            ["DS001"],
            "C50 乳房の悪性新生物",
            "解析方法の説明",
            "task_123",
        )

        # アサーション
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], DatasetAnalysisResult)
        assert result[0].id == "DS001"
        assert result[0].icd10 == "C50"
        assert result[0].analysis_method_similarity == "高"
        assert result[0].analysis_method_similarity_reason == "理由"
        assert result[0].url == "https://example.com/dataset"


@pytest.mark.asyncio
class TestReportGeneration:
    """レポート生成関数のテストクラス"""

    @patch("app.report_template")
    @patch("builtins.open", new_callable=mock_open)
    async def test_create_assessment_report(self, mock_file, mock_template):
        """create_assessment_report関数のテスト"""
        # モックの戻り値を設定
        mock_template.render.return_value = "テストレポート"

        # テストデータ
        application_id = "APP123"
        abstract_icd10 = "C50 乳房の悪性新生物"
        dataset_info_list = [
            DatasetAnalysisResult(
                id="DS001",
                icd10="C50",
                purpose_similarity=True,
                paper_similarity=True,
                analysis_method_similarity="高",
                analysis_method_similarity_reason="理由",
                analysis_method_details="詳細",
                url="https://example.com/dataset",
            )
        ]
        research_info_list = [
            ResearchInfo(
                title="テスト論文",
                doi="10.1234/test.123",
                authors=["山田 太郎"],
                abstract="テスト概要",
                url="https://example.com/paper",
                icd10="C50 乳房の悪性新生物",
            )
        ]
        research_abstract = "テスト研究概要"
        task_id = "task_123"

        # 関数を呼び出し
        result = await create_assessment_report(
            application_id,
            abstract_icd10,
            dataset_info_list,
            research_info_list,
            research_abstract,
            task_id,
        )

        # アサーション
        assert result == "テストレポート"
        mock_template.render.assert_called_once()
        mock_file.assert_called_once_with(
            f"results/{task_id}_report.md", "w", encoding="utf-8"
        )


class TestAPIEndpoints:
    """APIエンドポイントのテストクラス"""

    @patch("app.extract_data_from_pdf")
    @patch("fastapi.BackgroundTasks.add_task")
    @patch("os.makedirs")
    @patch("os.urandom")
    @patch("builtins.open", new_callable=mock_open)
    def test_submit_application(
        self,
        mock_file,
        mock_urandom,
        mock_makedirs,
        mock_bg_tasks_add_task,
        mock_extract_pdf,
    ):
        """submit_application関数のテスト"""
        # モックの設定
        mock_urandom.return_value = b"1234"
        mock_app_data = ApplicationData(
            application_id="APP123",
            dataset_id_list=["DS001"],
            related_studies_published=["10.1234/test.123"],
            research_abstract="研究概要",
            research_purpose="研究目的",
        )
        mock_extract_pdf.return_value = mock_app_data

        # テストリクエスト
        with open("dummy.pdf", "rb") as f:
            response = client.post(
                "/api/applications", files={"file": ("test.pdf", f, "application/pdf")}
            )

        # アサーション
        assert response.status_code == 202
        assert "task_id" in response.json()
        assert "message" in response.json()
        mock_bg_tasks_add_task.assert_called_once()

    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_get_application_status_processing(self, mock_file, mock_exists):
        """get_application_status関数の処理中ステータスのテスト"""
        # モックの設定
        mock_exists.return_value = False

        # テストリクエスト
        response = client.get("/api/applications/task_123")

        # アサーション
        assert response.status_code == 200
        assert response.json() == {"status": "processing", "task_id": "task_123"}

    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open)
    @patch("json.load")
    def test_get_application_status_completed(
        self, mock_json_load, mock_file, mock_exists
    ):
        """get_application_status関数の完了ステータスのテスト"""
        # モックの設定
        mock_exists.side_effect = lambda path: ".json" in path
        mock_json_load.return_value = {"assessment": "テスト結果"}

        # テストリクエスト
        response = client.get("/api/applications/task_123")

        # アサーション
        assert response.status_code == 200
        assert response.json() == {"assessment": "テスト結果"}


if __name__ == "__main__":
    unittest.main()
