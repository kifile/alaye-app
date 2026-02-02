import {
  ChevronDown,
  ChevronRight,
  Folder,
  FileText,
  Trash2,
  File,
  FolderOpen,
  Check,
  X,
  Edit3,
} from 'lucide-react';
import { useState, useCallback, useRef, useEffect, useReducer } from 'react';
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuSeparator,
  ContextMenuTrigger,
} from '@/components/ui/context-menu';
import { FileType } from '@/api/types';

export interface FileTreeNode {
  name: string;
  path: string;
  type: FileType;
  children?: FileTreeNode[];
}

interface EditorFileTreeProps {
  files: FileTreeNode[];
  selectedFile: string | null;
  onFileSelect: (file: FileTreeNode) => void;
  onFileCreate?: (parentPath: string, name: string, type: FileType) => void;
  onFileDelete?: (path: string) => void;
  onFileRename?: (path: string, newFilePath: string) => void;
  onFileMove?: (sourcePath: string, targetPath: string) => void;
  className?: string;
  readonly?: boolean;
}

// ============ State Management with useReducer ============

interface EditorTreeState {
  expandedFolders: Set<string>;
  newNode: NewNode | null;
  newNodeName: string;
  draggedNode: FileTreeNode | null;
  dragOverNode: string | null;
  editingNode: EditingNode | null;
  editingNodeName: string;
}

interface NewNode {
  id: string;
  parentPath: string;
  type: FileType;
  name: string;
}

interface EditingNode {
  path: string;
  type: FileType;
  name: string;
}

type EditorTreeAction =
  | { type: 'TOGGLE_FOLDER'; payload: string }
  | { type: 'SET_NEW_NODE'; payload: NewNode | null }
  | { type: 'SET_NEW_NODE_NAME'; payload: string }
  | { type: 'SET_DRAGGED_NODE'; payload: FileTreeNode | null }
  | { type: 'SET_DRAG_OVER_NODE'; payload: string | null }
  | { type: 'RESET_DRAG_STATE' }
  | { type: 'SET_EDITING_NODE'; payload: EditingNode | null }
  | { type: 'SET_EDITING_NODE_NAME'; payload: string };

function editorTreeReducer(
  state: EditorTreeState,
  action: EditorTreeAction
): EditorTreeState {
  switch (action.type) {
    case 'TOGGLE_FOLDER': {
      const newSet = new Set(state.expandedFolders);
      if (newSet.has(action.payload)) {
        newSet.delete(action.payload);
      } else {
        newSet.add(action.payload);
      }
      return { ...state, expandedFolders: newSet };
    }
    case 'SET_NEW_NODE':
      return { ...state, newNode: action.payload };
    case 'SET_NEW_NODE_NAME':
      return { ...state, newNodeName: action.payload };
    case 'SET_DRAGGED_NODE':
      return { ...state, draggedNode: action.payload };
    case 'SET_DRAG_OVER_NODE':
      return { ...state, dragOverNode: action.payload };
    case 'RESET_DRAG_STATE':
      return { ...state, draggedNode: null, dragOverNode: null };
    case 'SET_EDITING_NODE':
      return { ...state, editingNode: action.payload };
    case 'SET_EDITING_NODE_NAME':
      return { ...state, editingNodeName: action.payload };
    default:
      return state;
  }
}

// ============ EditorFileTree Component ============

export function EditorFileTree({
  files,
  selectedFile,
  onFileSelect,
  onFileCreate,
  onFileDelete,
  onFileRename,
  onFileMove,
  className = '',
  readonly = false,
}: EditorFileTreeProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  // 使用 useReducer 管理状态
  const [state, dispatch] = useReducer(editorTreeReducer, {
    expandedFolders: new Set<string>(),
    newNode: null,
    newNodeName: '',
    draggedNode: null,
    dragOverNode: null,
    editingNode: null,
    editingNodeName: '',
  });

  // 切换文件夹展开状态
  const toggleFolder = useCallback((path: string) => {
    dispatch({ type: 'TOGGLE_FOLDER', payload: path });
  }, []);

  // 处理文件点击
  const handleFileClick = useCallback(
    (file: FileTreeNode) => {
      if (file.type === FileType.FILE) {
        onFileSelect(file);
      } else {
        toggleFolder(file.path);
      }
    },
    [onFileSelect, toggleFolder]
  );

  // 开始创建新文件/文件夹
  const handleCreate = useCallback((node: FileTreeNode, type: FileType) => {
    // 创建新节点状态
    const id = `new-${Date.now()}`;
    dispatch({
      type: 'SET_NEW_NODE',
      payload: {
        id,
        parentPath: node.path,
        type,
        name: '',
      },
    });
    dispatch({ type: 'SET_NEW_NODE_NAME', payload: '' });
  }, []);

  // 取消新建
  const cancelNewNode = useCallback(() => {
    dispatch({ type: 'SET_NEW_NODE', payload: null });
    dispatch({ type: 'SET_NEW_NODE_NAME', payload: '' });
  }, []);

  // 确认新建
  const confirmNewNode = useCallback(() => {
    if (!state.newNode || !state.newNodeName.trim()) return;

    if (onFileCreate) {
      onFileCreate(
        state.newNode.parentPath,
        state.newNodeName.trim(),
        state.newNode.type
      );
    }
    cancelNewNode();
  }, [state.newNode, state.newNodeName, onFileCreate, cancelNewNode]);

  // 开始重命名
  const handleRename = useCallback((node: FileTreeNode) => {
    // 检查是否为 SKILL.md 主文件，不允许重命名
    if (node.name === 'SKILL.md') {
      return;
    }
    dispatch({
      type: 'SET_EDITING_NODE',
      payload: {
        path: node.path,
        type: node.type,
        name: node.name,
      },
    });
    dispatch({ type: 'SET_EDITING_NODE_NAME', payload: node.name });
  }, []);

  // 取消重命名
  const cancelRename = useCallback(() => {
    dispatch({ type: 'SET_EDITING_NODE', payload: null });
    dispatch({ type: 'SET_EDITING_NODE_NAME', payload: '' });
  }, []);

  // 确认重命名
  const confirmRename = useCallback(() => {
    if (!state.editingNode || !state.editingNodeName.trim()) return;

    if (onFileRename) {
      onFileRename(state.editingNode.path, state.editingNodeName.trim());
    }
    cancelRename();
  }, [state.editingNode, state.editingNodeName, onFileRename, cancelRename]);

  // 处理输入框回车
  const handleInputKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        e.stopPropagation();
        if (state.editingNode) {
          confirmRename();
        } else {
          confirmNewNode();
        }
      } else if (e.key === 'Escape') {
        e.preventDefault();
        e.stopPropagation();
        if (state.editingNode) {
          cancelRename();
        } else {
          cancelNewNode();
        }
      }
    },
    [
      state.editingNode,
      state.newNode,
      confirmRename,
      cancelRename,
      confirmNewNode,
      cancelNewNode,
    ]
  );

  // 当编辑状态改变时，自动聚焦输入框
  useEffect(() => {
    if ((state.newNode || state.editingNode) && inputRef.current) {
      inputRef.current.focus();
    }
  }, [state.newNode, state.editingNode]);

  // 删除文件/文件夹
  const handleDelete = useCallback(
    (path: string) => {
      // 检查是否为 SKILL.md 主文件，不允许删除
      const isMainFile = path === 'SKILL.md' || path.endsWith('/SKILL.md');
      if (isMainFile) {
        return;
      }

      if (onFileDelete) {
        if (confirm(`Are you sure you want to delete this?`)) {
          onFileDelete(path);
        }
      }
    },
    [onFileDelete]
  );

  // 拖拽开始
  const handleDragStart = useCallback((e: React.DragEvent, node: FileTreeNode) => {
    // 检查是否为 SKILL.md 主文件，不允许拖拽
    if (node.name === 'SKILL.md') {
      e.preventDefault();
      return;
    }
    dispatch({ type: 'SET_DRAGGED_NODE', payload: node });
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', node.path);
  }, []);

  // 拖拽结束
  const handleDragEnd = useCallback(() => {
    dispatch({ type: 'RESET_DRAG_STATE' });
  }, []);

  // 拖拽经过
  const handleDragOver = useCallback((e: React.DragEvent, node: FileTreeNode) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    if (node.type === FileType.DIRECTORY) {
      dispatch({ type: 'SET_DRAG_OVER_NODE', payload: node.path });
    }
  }, []);

  // 拖拽离开
  const handleDragLeave = useCallback(() => {
    dispatch({ type: 'SET_DRAG_OVER_NODE', payload: null });
  }, []);

  // 放置
  const handleDrop = useCallback(
    (e: React.DragEvent, targetNode: FileTreeNode) => {
      e.preventDefault();
      e.stopPropagation();

      if (state.draggedNode && targetNode.type === FileType.DIRECTORY && onFileMove) {
        // 不能移动到自己的子目录中
        if (!state.draggedNode.path.startsWith(targetNode.path)) {
          onFileMove(state.draggedNode.path, targetNode.path);
        }
      }

      dispatch({ type: 'RESET_DRAG_STATE' });
    },
    [state.draggedNode, onFileMove]
  );

  // 递归渲染文件树节点（不使用 useCallback，因为它是递归函数且依赖很多状态）
  const renderNode = (node: FileTreeNode, level: number = 0) => {
    const isSelected = selectedFile === node.path;
    const isExpanded = state.expandedFolders.has(node.path);
    const isDragOver = state.dragOverNode === node.path;
    const paddingLeft = level * 16 + 8;

    // 检查是否在编辑模式
    const isEditing = state.editingNode?.path === node.path;
    // 检查是否需要在当前目录下显示新节点
    const showNewNode = state.newNode && node.path === state.newNode.parentPath;

    // 检查是否为 SKILL.md 主文件
    const isMainFile = node.name === 'SKILL.md';

    if (node.type === FileType.DIRECTORY) {
      return (
        <div key={node.path}>
          <ContextMenu>
            <ContextMenuTrigger asChild>
              <div
                draggable={!readonly}
                onDragStart={!readonly ? e => handleDragStart(e, node) : undefined}
                onDragEnd={!readonly ? handleDragEnd : undefined}
                onDragOver={!readonly ? e => handleDragOver(e, node) : undefined}
                onDragLeave={!readonly ? handleDragLeave : undefined}
                onDrop={!readonly ? e => handleDrop(e, node) : undefined}
                onClick={() => toggleFolder(node.path)}
                className={`flex items-center gap-1.5 w-full px-2 py-1.5 rounded transition-colors cursor-pointer ${
                  isEditing
                    ? 'bg-sky-50 border-2 border-sky-300'
                    : isDragOver
                      ? 'bg-sky-200'
                      : 'hover:bg-accent/50'
                }`}
                style={{ paddingLeft: `${paddingLeft}px` }}
              >
                <div className='flex-shrink-0'>
                  {isExpanded ? (
                    <ChevronDown className='h-3.5 w-3.5 text-muted-foreground' />
                  ) : (
                    <ChevronRight className='h-3.5 w-3.5 text-muted-foreground' />
                  )}
                </div>
                {isExpanded ? (
                  <FolderOpen className='h-4 w-4 text-blue-500 flex-shrink-0' />
                ) : (
                  <Folder className='h-4 w-4 text-blue-500 flex-shrink-0' />
                )}
                {isEditing ? (
                  <>
                    <input
                      ref={inputRef}
                      type='text'
                      value={state.editingNodeName}
                      onChange={e =>
                        dispatch({
                          type: 'SET_EDITING_NODE_NAME',
                          payload: e.target.value,
                        })
                      }
                      onKeyDown={handleInputKeyDown}
                      className='flex-1 text-xs bg-transparent border-none outline-none text-foreground'
                      autoFocus
                    />
                    <button
                      onClick={e => {
                        e.stopPropagation();
                        confirmRename();
                      }}
                      className='flex-shrink-0 p-0.5 hover:bg-sky-200 rounded'
                      title='Confirm (Enter)'
                    >
                      <Check className='h-3 w-3 text-green-600' />
                    </button>
                    <button
                      onClick={e => {
                        e.stopPropagation();
                        cancelRename();
                      }}
                      className='flex-shrink-0 p-0.5 hover:bg-sky-200 rounded'
                      title='Cancel (Esc)'
                    >
                      <X className='h-3 w-3 text-red-600' />
                    </button>
                  </>
                ) : (
                  <span className='text-xs font-medium text-foreground flex-1 text-left truncate'>
                    {node.name}
                  </span>
                )}
                {node.children && node.children.length > 0 && !isEditing && (
                  <span className='text-xs text-muted-foreground'>
                    ({node.children.length})
                  </span>
                )}
              </div>
            </ContextMenuTrigger>
            {!readonly && !isEditing && (
              <ContextMenuContent>
                <ContextMenuItem onClick={() => handleCreate(node, FileType.FILE)}>
                  <File className='h-3.5 w-3.5' />
                  New File
                </ContextMenuItem>
                <ContextMenuItem onClick={() => handleCreate(node, FileType.DIRECTORY)}>
                  <Folder className='h-3.5 w-3.5' />
                  New Folder
                </ContextMenuItem>
                {node.name !== 'root' && (
                  <>
                    <ContextMenuSeparator />
                    <ContextMenuItem onClick={() => handleRename(node)}>
                      <Edit3 className='h-3.5 w-3.5' />
                      Rename
                    </ContextMenuItem>
                    <ContextMenuItem
                      variant='destructive'
                      onClick={() => handleDelete(node.path)}
                    >
                      <Trash2 className='h-3.5 w-3.5' />
                      Delete
                    </ContextMenuItem>
                  </>
                )}
              </ContextMenuContent>
            )}
          </ContextMenu>
          {isExpanded && (
            <div className='mt-0.5'>
              {node.children?.map(child => renderNode(child, level + 1)) || null}
              {showNewNode && renderNewNode(level + 1)}
            </div>
          )}
        </div>
      );
    }

    // 文件节点
    return (
      <ContextMenu key={node.path}>
        <ContextMenuTrigger asChild>
          <div
            draggable={!readonly && !isMainFile}
            onDragStart={
              !readonly && !isMainFile ? e => handleDragStart(e, node) : undefined
            }
            onDragEnd={!readonly && !isMainFile ? handleDragEnd : undefined}
            onDragOver={
              !readonly && !isMainFile ? e => handleDragOver(e, node) : undefined
            }
            onDragLeave={!readonly && !isMainFile ? handleDragLeave : undefined}
            onDrop={!readonly && !isMainFile ? e => handleDrop(e, node) : undefined}
            onClick={() => handleFileClick(node)}
            className={`flex items-center gap-1.5 w-full px-2 py-1.5 rounded transition-colors text-left ${
              isEditing
                ? 'bg-sky-50 border-2 border-sky-300'
                : readonly
                  ? 'cursor-pointer'
                  : isMainFile
                    ? 'cursor-default'
                    : 'cursor-move'
            } ${
              !isEditing &&
              (isSelected
                ? 'bg-sky-100 text-foreground font-medium'
                : 'hover:bg-accent/50 text-muted-foreground')
            }`}
            style={{ paddingLeft: `${paddingLeft}px` }}
          >
            <div className='w-[14px] flex-shrink-0' />{' '}
            {/* 占位，保持与文件夹箭头对齐 (14px = 3.5 * 4px) */}
            {isEditing ? (
              <>
                <FileText className='h-4 w-4 flex-shrink-0 text-muted-foreground' />
                <input
                  ref={inputRef}
                  type='text'
                  value={state.editingNodeName}
                  onChange={e =>
                    dispatch({ type: 'SET_EDITING_NODE_NAME', payload: e.target.value })
                  }
                  onKeyDown={handleInputKeyDown}
                  className='flex-1 text-xs bg-transparent border-none outline-none text-foreground'
                  autoFocus
                />
                <button
                  onClick={e => {
                    e.stopPropagation();
                    confirmRename();
                  }}
                  className='flex-shrink-0 p-0.5 hover:bg-sky-200 rounded'
                  title='Confirm (Enter)'
                >
                  <Check className='h-3 w-3 text-green-600' />
                </button>
                <button
                  onClick={e => {
                    e.stopPropagation();
                    cancelRename();
                  }}
                  className='flex-shrink-0 p-0.5 hover:bg-sky-200 rounded'
                  title='Cancel (Esc)'
                >
                  <X className='h-3 w-3 text-red-600' />
                </button>
              </>
            ) : (
              <>
                <FileText
                  className={`h-4 w-4 flex-shrink-0 ${
                    isSelected ? 'text-sky-600' : 'text-muted-foreground'
                  }`}
                />
                <span className='text-xs flex-1 truncate'>{node.name}</span>
              </>
            )}
          </div>
        </ContextMenuTrigger>
        {!readonly && !isEditing && !isMainFile && (
          <ContextMenuContent>
            <ContextMenuItem onClick={() => handleRename(node)}>
              <Edit3 className='h-3.5 w-3.5' />
              Rename
            </ContextMenuItem>
            <ContextMenuItem
              variant='destructive'
              onClick={() => handleDelete(node.path)}
            >
              <Trash2 className='h-3.5 w-3.5' />
              Delete
            </ContextMenuItem>
          </ContextMenuContent>
        )}
      </ContextMenu>
    );
  };

  // 渲染新节点（输入框状态）
  const renderNewNode = useCallback(
    (level: number = 0) => {
      if (!state.newNode) return null;

      const paddingLeft = level * 16 + 8;
      const icon =
        state.newNode.type === FileType.DIRECTORY ? (
          <Folder className='h-4 w-4 text-blue-500 flex-shrink-0' />
        ) : (
          <FileText className='h-4 w-4 text-muted-foreground flex-shrink-0' />
        );

      return (
        <div
          key={state.newNode.id}
          className={`flex items-center gap-1.5 w-full px-2 py-1.5 rounded bg-sky-50 border-2 border-sky-300`}
          style={{ paddingLeft: `${paddingLeft}px` }}
        >
          <div className='w-[14px] flex-shrink-0' />
          {icon}
          <input
            ref={inputRef}
            type='text'
            value={state.newNodeName}
            onChange={e =>
              dispatch({ type: 'SET_NEW_NODE_NAME', payload: e.target.value })
            }
            onKeyDown={handleInputKeyDown}
            className='flex-1 text-xs bg-transparent border-none outline-none text-foreground'
            placeholder={
              state.newNode.type === FileType.DIRECTORY
                ? 'New folder name'
                : 'New file name'
            }
            autoFocus
          />
          <button
            onClick={confirmNewNode}
            className='flex-shrink-0 p-0.5 hover:bg-sky-200 rounded'
            title='Confirm (Enter)'
          >
            <Check className='h-3 w-3 text-green-600' />
          </button>
          <button
            onClick={cancelNewNode}
            className='flex-shrink-0 p-0.5 hover:bg-sky-200 rounded'
            title='Cancel (Esc)'
          >
            <X className='h-3 w-3 text-red-600' />
          </button>
        </div>
      );
    },
    [
      state.newNode,
      state.newNodeName,
      confirmNewNode,
      cancelNewNode,
      handleInputKeyDown,
    ]
  );

  // 渲染编辑节点（重命名输入框）
  const renderEditingNode = useCallback(
    (level: number = 0) => {
      if (!state.editingNode) return null;

      const paddingLeft = level * 16 + 8;
      const icon =
        state.editingNode.type === FileType.DIRECTORY ? (
          <Folder className='h-4 w-4 text-blue-500 flex-shrink-0' />
        ) : (
          <FileText className='h-4 w-4 text-muted-foreground flex-shrink-0' />
        );

      return (
        <div
          key={`editing-${state.editingNode.path}`}
          className={`flex items-center gap-1.5 w-full px-2 py-1.5 rounded bg-sky-50 border-2 border-sky-300`}
          style={{ paddingLeft: `${paddingLeft}px` }}
        >
          <div className='w-[14px] flex-shrink-0' />
          {icon}
          <input
            ref={inputRef}
            type='text'
            value={state.editingNodeName}
            onChange={e =>
              dispatch({ type: 'SET_EDITING_NODE_NAME', payload: e.target.value })
            }
            onKeyDown={handleInputKeyDown}
            className='flex-1 text-xs bg-transparent border-none outline-none text-foreground'
            autoFocus
          />
          <button
            onClick={confirmRename}
            className='flex-shrink-0 p-0.5 hover:bg-sky-200 rounded'
            title='Confirm (Enter)'
          >
            <Check className='h-3 w-3 text-green-600' />
          </button>
          <button
            onClick={cancelRename}
            className='flex-shrink-0 p-0.5 hover:bg-sky-200 rounded'
            title='Cancel (Esc)'
          >
            <X className='h-3 w-3 text-red-600' />
          </button>
        </div>
      );
    },
    [
      state.editingNode,
      state.editingNodeName,
      confirmRename,
      cancelRename,
      handleInputKeyDown,
    ]
  );

  // 如果没有文件，不渲染
  if (!files || files.length === 0) {
    return null;
  }

  // 虚拟根目录节点，用于在空白区域右键时创建文件/文件夹
  const rootNode: FileTreeNode = {
    name: 'root',
    path: '',
    type: FileType.DIRECTORY,
    children: files,
  };

  return (
    <div
      className={`flex flex-col bg-slate-50 border-r border-border h-full ${className}`}
      style={{ width: '280px' }}
    >
      {/* File Tree */}
      <ContextMenu>
        <ContextMenuTrigger asChild>
          <div
            className='flex-1 overflow-y-auto px-2 py-2 min-h-0'
            onClick={e => {
              // 如果正在新建或重命名，点击其他地方时确认
              if (state.newNode || state.editingNode) {
                // 检查点击是否发生在编辑容器内
                const target = e.target as HTMLElement;
                const isNewNodeContainer = target.closest('.bg-sky-50.border-sky-300');
                // 如果点击的不是编辑容器，也不是确认/取消按钮，则确认
                if (!isNewNodeContainer) {
                  if (state.newNode) {
                    confirmNewNode();
                  } else if (state.editingNode) {
                    confirmRename();
                  }
                }
              }
            }}
          >
            {files.map(file => renderNode(file))}
            {/* 如果是根目录创建新节点，显示在列表最后 */}
            {state.newNode && state.newNode.parentPath === '' && renderNewNode(0)}
          </div>
        </ContextMenuTrigger>
        {!readonly && (
          <ContextMenuContent>
            <ContextMenuItem onClick={() => handleCreate(rootNode, FileType.FILE)}>
              <File className='h-3.5 w-3.5' />
              New File
            </ContextMenuItem>
            <ContextMenuItem onClick={() => handleCreate(rootNode, FileType.DIRECTORY)}>
              <Folder className='h-3.5 w-3.5' />
              New Folder
            </ContextMenuItem>
          </ContextMenuContent>
        )}
      </ContextMenu>
    </div>
  );
}
