"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Search, AlertCircle, CheckCircle2, Clock, FileText, RefreshCw } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

// APIのベースURL
// APIのベースURL
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL 

type TaskStatus = "pending" | "processing" | "completed" | "failed"

interface TaskDetails {
  id?: string
  task_id?: string
  status: TaskStatus
  filename?: string
  created_at?: string
  updated_at?: string
  message?: string
  result?: string
  error?: string
  // APIレスポンスに合わせて追加のフィールドを定義
  [key: string]: any
}

interface TaskStatusProps {
  currentTaskId: string | null
}

export default function TaskStatus({ currentTaskId }: TaskStatusProps) {
  const [taskId, setTaskId] = useState("")
  const [taskIds, setTaskIds] = useState<string[]>([])
  const [loadingTaskIds, setLoadingTaskIds] = useState(false)
  const [loading, setLoading] = useState(false)
  const [taskDetails, setTaskDetails] = useState<TaskDetails | null>(null)
  const [error, setError] = useState<string | null>(null)

  // コンポーネントマウント時とcurrentTaskIdが変更された時にタスクID一覧を取得
  useEffect(() => {
    fetchTaskIds()
  }, [])

  // 親コンポーネントからタスクIDが渡された場合、自動的に設定して検索
  useEffect(() => {
    if (currentTaskId) {
      setTaskId(currentTaskId)
      fetchTaskDetails(currentTaskId)
    }
  }, [currentTaskId])

  // タスクID一覧を取得する関数
  const fetchTaskIds = async () => {
    setLoadingTaskIds(true)
    setError(null)

    try {
      const response = await fetch(`${API_BASE_URL}/api/applications`, {
        headers: {
          "ngrok-skip-browser-warning": "true",
        },
      })

      if (!response.ok) {
        throw new Error("タスクID一覧の取得に失敗しました")
      }

      const data = await response.json()

      // APIのレスポンス形式に合わせて調整
      // 想定されるレスポンス形式: { task_ids: ["id1", "id2", ...] } または ["id1", "id2", ...]
      let ids: string[] = []

      ids = data.tasks.map((task) => String(task.task_id))
      setTaskIds(ids)

      // 現在のタスクIDがない場合、最初のタスクIDを選択
      if ((!taskId || taskId === "") && ids.length > 0) {
        setTaskId(ids[0])
        fetchTaskDetails(ids[0])
      }
    } catch (err) {
      console.error("タスクID一覧の取得エラー:", err)
      setError(err instanceof Error ? err.message : "タスクID一覧の取得に失敗しました")
    } finally {
      setLoadingTaskIds(false)
    }
  }

  const fetchTaskDetails = async (id: string | number) => {
    // idを文字列に変換
    const taskIdStr = String(id)

    if (!taskIdStr || taskIdStr === "") {
      setError("タスクIDを選択してください")
      return
    }

    setLoading(true)
    setError(null)

    try {
      // 実際のAPIエンドポイントからタスク状況を取得
      const response = await fetch(`${API_BASE_URL}/api/applications/${taskIdStr}`, {
        headers: {
          "ngrok-skip-browser-warning": "true",
        },
      })

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error("指定されたタスクが見つかりません")
        }
        const errorData = await response.json()
        throw new Error(errorData.detail || "タスク情報の取得に失敗しました")
      }

      const data = await response.json()

      // APIのレスポンス形式に合わせてデータを整形
      const formattedData: TaskDetails = {
        id: String(data.task_id || data.id || taskIdStr),
        task_id: String(data.task_id || data.id || taskIdStr),
        status: mapStatus(data.status),
        filename: data.filename || "申請書.pdf",
        created_at: data.created_at || data.createdAt || new Date().toISOString(),
        updated_at: data.updated_at || data.updatedAt || new Date().toISOString(),
        message: data.message,
        result: data.result || data.markdown_result || data.markdownResult,
        ...data, // その他のフィールドも保持
      }

      setTaskDetails(formattedData)
    } catch (err) {
      setError(err instanceof Error ? err.message : "タスク情報の取得に失敗しました")
    } finally {
      setLoading(false)
    }
  }

  // APIのステータス値をアプリケーションで使用する値にマッピング
  const mapStatus = (apiStatus: string): TaskStatus => {
    if (!apiStatus) return "processing"

    const statusMap: Record<string, TaskStatus> = {
      pending: "pending",
      processing: "processing",
      completed: "completed",
      failed: "failed",
      success: "completed",
      error: "failed",
      in_progress: "processing",
      waiting: "pending",
    }

    return statusMap[apiStatus.toLowerCase()] || "processing"
  }

  const handleTaskIdChange = (value: string) => {
    setTaskId(value)
    fetchTaskDetails(value)
  }

  const getStatusBadge = (status: TaskStatus) => {
    switch (status) {
      case "pending":
        return (
          <Badge variant="outline" className="bg-yellow-50 text-yellow-700 border-yellow-200">
            待機中
          </Badge>
        )
      case "processing":
        return (
          <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">
            処理中
          </Badge>
        )
      case "completed":
        return (
          <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
            完了
          </Badge>
        )
      case "failed":
        return (
          <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200">
            失敗
          </Badge>
        )
    }
  }

  const getStatusIcon = (status: TaskStatus) => {
    switch (status) {
      case "pending":
        return <Clock className="h-5 w-5 text-yellow-500" />
      case "processing":
        return <Clock className="h-5 w-5 text-blue-500 animate-pulse" />
      case "completed":
        return <CheckCircle2 className="h-5 w-5 text-green-500" />
      case "failed":
        return <AlertCircle className="h-5 w-5 text-red-500" />
    }
  }

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <div className="text-sm font-medium">タスクID</div>
          <Button variant="ghost" size="sm" onClick={fetchTaskIds} disabled={loadingTaskIds} className="h-8 px-2">
            <RefreshCw className={`h-4 w-4 ${loadingTaskIds ? "animate-spin" : ""}`} />
            <span className="sr-only">更新</span>
          </Button>
        </div>

        <div className="flex items-center gap-2">
          <Select value={taskId} onValueChange={handleTaskIdChange} disabled={loadingTaskIds || taskIds.length === 0}>
            <SelectTrigger className="flex-1">
              <SelectValue placeholder="タスクIDを選択" />
            </SelectTrigger>
            <SelectContent>
              {taskIds.map((id) => (
                <SelectItem key={id} value={id}>
                  {id}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Button onClick={() => taskId && fetchTaskDetails(taskId)} disabled={loading || !taskId}>
            <Search className="mr-2 h-4 w-4" />
            検索
          </Button>
        </div>
      </div>

      {loadingTaskIds && taskIds.length === 0 && (
        <div className="flex justify-center py-2">
          <div className="text-sm text-muted-foreground">タスクID一覧を読み込み中...</div>
        </div>
      )}

      {!loadingTaskIds && taskIds.length === 0 && (
        <Alert>
          <AlertDescription>
            利用可能なタスクIDがありません。申請書PDFをアップロードしてタスクを作成してください。
          </AlertDescription>
        </Alert>
      )}

      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {loading && (
        <div className="flex justify-center py-4">
          <div className="animate-pulse text-blue-500">データを読み込み中...</div>
        </div>
      )}

      {taskDetails && (
        <Card>
          <CardContent className="pt-6">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {getStatusIcon(taskDetails.status)}
                  <h3 className="text-lg font-medium">タスク: {taskDetails.task_id || taskDetails.id}</h3>
                </div>
                {getStatusBadge(taskDetails.status)}
              </div>

              <div className="space-y-2">
                {taskDetails.filename && (
                  <div className="flex items-center gap-2">
                    <FileText className="h-4 w-4 text-gray-500" />
                    <span className="text-sm text-gray-700">ファイル名: {taskDetails.filename}</span>
                  </div>
                )}

                {taskDetails.created_at && (
                  <div className="text-sm text-gray-500">
                    <p>作成日時: {new Date(taskDetails.created_at).toLocaleString("ja-JP")}</p>
                    {taskDetails.updated_at && (
                      <p>更新日時: {new Date(taskDetails.updated_at).toLocaleString("ja-JP")}</p>
                    )}
                  </div>
                )}

                {taskDetails.message && (
                  <Alert variant={taskDetails.status === "failed" ? "destructive" : "default"}>
                    <AlertDescription>{taskDetails.message}</AlertDescription>
                  </Alert>
                )}

                {taskDetails.error && (
                  <Alert variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>{taskDetails.error}</AlertDescription>
                  </Alert>
                )}

                {taskDetails.result && (
                  <div className="mt-6 border rounded-md p-4 bg-white">
                    <h4 className="text-sm font-medium mb-2">処理結果</h4>
                    <div className="prose prose-sm max-w-none">
                      <div className="markdown-body">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {taskDetails.result}
                        </ReactMarkdown>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
