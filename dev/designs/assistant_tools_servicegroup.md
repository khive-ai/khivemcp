# AssistantTools ServiceGroup Design

## Overview

The `AssistantTools` ServiceGroup provides a collection of operations that enhance AI assistants' capabilities, enabling them to perform tasks beyond their native abilities. This includes web search, file analysis, code repository exploration, data visualization, and more.

## ServiceGroup Design

### `AssistantToolsGroup` Class

The main ServiceGroup class will organize related tools for AI assistants:

```python
class AssistantToolsGroup(ServiceGroup):
    """Collection of tools to enhance AI assistant capabilities."""
    
    def __init__(self):
        super().__init__()
        # Initialize components like web search client, visualization engine, etc.
        self._search_client = None
        self._file_analyzer = None
        self._repo_analyzer = None
        self._viz_engine = None
```

### Operations

#### Web Search Functionality

```python
@operation(schema=WebSearchSchema)
async def web_search(self, query: WebSearchSchema, ctx: Context) -> List[SearchResult]:
    """Search the web for information.
    
    Args:
        query: Search parameters including query string, result limit, etc.
        ctx: MCP context for progress reporting and logging
        
    Returns:
        List of search results with title, URL, snippet, and source.
    """
    # Implementation will use search API client
    # Report progress during search and processing
```

Input Schema:
```python
class WebSearchSchema(BaseModel):
    """Parameters for web search."""
    query: str = Field(..., description="Search query string")
    result_limit: int = Field(5, description="Maximum number of results to return", ge=1, le=20)
    safe_search: bool = Field(True, description="Whether to enable safe search filtering")
    search_type: SearchType = Field(SearchType.WEB, description="Type of search to perform")
    
class SearchType(str, Enum):
    """Types of searches available."""
    WEB = "web"
    NEWS = "news"
    IMAGES = "images"
    SCHOLARLY = "scholarly"
```

Output Format:
```python
class SearchResult(BaseModel):
    """Structure of a search result."""
    title: str
    url: str
    snippet: str
    source: str
    date_published: Optional[datetime] = None
    image_url: Optional[str] = None
```

#### File Analysis/Summarization

```python
@operation(schema=FileAnalysisSchema)
async def analyze_file(self, file_input: FileAnalysisSchema, ctx: Context) -> FileAnalysisResult:
    """Analyze and summarize a file.
    
    Args:
        file_input: File path or content and analysis parameters
        ctx: MCP context for progress reporting and logging
        
    Returns:
        Analysis results including summary, key points, and metadata.
    """
    # Implementation will handle different file types
    # Extract text content from documents, analyze code, summarize data
```

Input Schema:
```python
class FileAnalysisSchema(BaseModel):
    """Parameters for file analysis."""
    file_path: Optional[str] = Field(None, description="Path to the file (local or URL)")
    file_content: Optional[str] = Field(None, description="Raw file content if path is not provided")
    analysis_type: AnalysisType = Field(AnalysisType.AUTO, description="Type of analysis to perform")
    depth: AnalysisDepth = Field(AnalysisDepth.STANDARD, description="Depth of analysis")
    
    @model_validator(mode='after')
    def check_file_source(self) -> 'FileAnalysisSchema':
        if not self.file_path and not self.file_content:
            raise ValueError("Either file_path or file_content must be provided")
        return self
    
class AnalysisType(str, Enum):
    """Types of file analysis available."""
    AUTO = "auto"  # Determine type from file extension
    TEXT = "text"  # Plain text analysis
    CODE = "code"  # Source code analysis
    DATA = "data"  # Structured data analysis (CSV, JSON, etc.)
    DOCUMENT = "document"  # Document analysis (PDF, DOCX, etc.)
    
class AnalysisDepth(str, Enum):
    """Depth levels for analysis."""
    QUICK = "quick"  # High-level overview
    STANDARD = "standard"  # Balanced depth analysis
    DETAILED = "detailed"  # In-depth analysis
```

Output Format:
```python
class FileAnalysisResult(BaseModel):
    """Results of file analysis."""
    summary: str
    key_points: List[str]
    metadata: Dict[str, Any]
    detected_type: str
    detected_language: Optional[str] = None
    word_count: Optional[int] = None
    structure: Optional[List[Dict[str, Any]]] = None  # Hierarchical structure if applicable
    recommendations: Optional[List[str]] = None
```

#### Code Repository Analysis

```python
@operation(schema=RepoAnalysisSchema)
async def analyze_repo(self, repo_input: RepoAnalysisSchema, ctx: Context) -> RepoAnalysisResult:
    """Analyze a code repository structure and provide insights.
    
    Args:
        repo_input: Repository URL or path and analysis parameters
        ctx: MCP context for progress reporting and logging
        
    Returns:
        Analysis of the repository including structure, components, and insights.
    """
    # Implementation will clone or access local repo
    # Analyze structure, dependencies, etc.
```

Input Schema:
```python
class RepoAnalysisSchema(BaseModel):
    """Parameters for repository analysis."""
    repo_url: Optional[str] = Field(None, description="Git repository URL")
    repo_path: Optional[str] = Field(None, description="Local path to repository")
    analysis_focus: List[AnalysisFocus] = Field(
        [AnalysisFocus.STRUCTURE], description="What aspects to focus analysis on"
    )
    include_contents: bool = Field(False, description="Whether to include file contents in analysis")
    
    @model_validator(mode='after')
    def check_repo_source(self) -> 'RepoAnalysisSchema':
        if not self.repo_url and not self.repo_path:
            raise ValueError("Either repo_url or repo_path must be provided")
        return self
    
class AnalysisFocus(str, Enum):
    """Focus areas for repository analysis."""
    STRUCTURE = "structure"  # Directory and file structure
    DEPENDENCIES = "dependencies"  # Project dependencies
    ARCHITECTURE = "architecture"  # Software architecture patterns
    CONTRIBUTORS = "contributors"  # Contribution patterns
    COMPLEXITY = "complexity"  # Code complexity metrics
```

Output Format:
```python
class RepoAnalysisResult(BaseModel):
    """Results of repository analysis."""
    repo_name: str
    language_breakdown: Dict[str, float]  # Language: percentage
    directory_structure: Dict[str, Any]  # Hierarchical directory structure
    key_components: List[Dict[str, str]]  # Important files/directories with descriptions
    dependencies: Optional[List[Dict[str, str]]] = None
    contributor_stats: Optional[Dict[str, Any]] = None
    architecture_insights: Optional[List[str]] = None
    complexity_metrics: Optional[Dict[str, Any]] = None
    recommendations: List[str]
```

#### Data Visualization

```python
@operation(schema=DataVisualizationSchema)
async def visualize_data(self, viz_input: DataVisualizationSchema, ctx: Context) -> Image:
    """Generate data visualizations from structured data.
    
    Args:
        viz_input: Data and visualization parameters
        ctx: MCP context for progress reporting and logging
        
    Returns:
        Generated visualization as an image.
    """
    # Implementation will use visualization libraries
    # Generate charts, graphs, plots based on data
```

Input Schema:
```python
class DataVisualizationSchema(BaseModel):
    """Parameters for data visualization."""
    data: Union[str, List[Dict[str, Any]]] = Field(
        ..., description="Data source (CSV string, JSON array, or list of dictionaries)"
    )
    chart_type: ChartType = Field(..., description="Type of chart to generate")
    title: Optional[str] = Field(None, description="Chart title")
    x_axis: Optional[str] = Field(None, description="Column/key to use for x-axis")
    y_axis: Union[str, List[str], None] = Field(None, description="Column(s)/key(s) to use for y-axis")
    width: int = Field(800, description="Width of the chart in pixels", ge=400, le=2000)
    height: int = Field(600, description="Height of the chart in pixels", ge=300, le=1500)
    
class ChartType(str, Enum):
    """Types of charts available for visualization."""
    LINE = "line"
    BAR = "bar"
    SCATTER = "scatter"
    PIE = "pie"
    HEATMAP = "heatmap"
    BOX = "box"
    HISTOGRAM = "histogram"
```

#### Document Generation

```python
@operation(schema=DocumentGenerationSchema)
async def generate_document(self, doc_input: DocumentGenerationSchema, ctx: Context) -> DocumentResult:
    """Generate formatted documents from structured content.
    
    Args:
        doc_input: Document content and formatting parameters
        ctx: MCP context for progress reporting and logging
        
    Returns:
        Generated document information and download link.
    """
    # Implementation will format content into various document types
    # Support for PDF, DOCX, HTML, Markdown, etc.
```

Input Schema:
```python
class DocumentGenerationSchema(BaseModel):
    """Parameters for document generation."""
    content: str = Field(..., description="Content to include in the document")
    format: DocumentFormat = Field(DocumentFormat.PDF, description="Output document format")
    title: Optional[str] = Field(None, description="Document title")
    template: Optional[str] = Field(None, description="Template name or ID to use")
    metadata: Optional[Dict[str, str]] = Field(None, description="Document metadata")
    
class DocumentFormat(str, Enum):
    """Available document output formats."""
    PDF = "pdf"
    DOCX = "docx"
    HTML = "html"
    MARKDOWN = "markdown"
    TXT = "txt"
```

Output Format:
```python
class DocumentResult(BaseModel):
    """Results of document generation."""
    document_id: str
    title: str
    format: str
    download_url: str
    page_count: Optional[int] = None
    word_count: Optional[int] = None
    size_bytes: Optional[int] = None
```

#### Semantic Text Analysis

```python
@operation(schema=TextAnalysisSchema)
async def analyze_text(self, text_input: TextAnalysisSchema, ctx: Context) -> TextAnalysisResult:
    """Perform semantic analysis on text.
    
    Args:
        text_input: Text content and analysis parameters
        ctx: MCP context for progress reporting and logging
        
    Returns:
        Analysis results including entities, sentiment, etc.
    """
    # Implementation will use NLP libraries
    # Identify entities, sentiment, topics, etc.
```

Input Schema:
```python
class TextAnalysisSchema(BaseModel):
    """Parameters for text analysis."""
    text: str = Field(..., description="Text content to analyze")
    analysis_types: List[TextAnalysisType] = Field(
        [TextAnalysisType.ENTITIES, TextAnalysisType.SENTIMENT], 
        description="Types of analysis to perform"
    )
    language: Optional[str] = Field(None, description="ISO language code (auto-detect if None)")
    
class TextAnalysisType(str, Enum):
    """Types of text analysis available."""
    ENTITIES = "entities"  # Named entity recognition
    SENTIMENT = "sentiment"  # Sentiment analysis
    TOPICS = "topics"  # Topic extraction
    SUMMARY = "summary"  # Text summarization
    KEYWORDS = "keywords"  # Keyword extraction
    READABILITY = "readability"  # Readability metrics
```

Output Format:
```python
class TextAnalysisResult(BaseModel):
    """Results of text analysis."""
    detected_language: str
    word_count: int
    entities: Optional[List[Dict[str, Any]]] = None
    sentiment: Optional[Dict[str, float]] = None
    topics: Optional[List[Dict[str, Any]]] = None
    summary: Optional[str] = None
    keywords: Optional[List[str]] = None
    readability_metrics: Optional[Dict[str, Any]] = None
```

## Configuration File (YAML)

```yaml
name: assistant-tools
description: "Enhanced capabilities for AI assistants including web search, file analysis, and data visualization"
packages:
  - aiohttp>=3.8.0
  - pydantic>=2.0.0
  - pandas>=2.0.0
  - matplotlib>=3.7.0
  - nltk>=3.8.0
  - beautifulsoup4>=4.12.0
  - PyPDF2>=3.0.0
  - python-docx>=0.8.11
  - pygit2>=1.12.0
  - numpy>=1.24.0
  - requests>=2.28.0
  - pillow>=10.0.0
  - plotly>=5.15.0
  - jinja2>=3.1.0
  - fastapi>=0.100.0
  - uvicorn>=0.23.0
env_vars:
  - SEARCH_API_KEY
  - TEMP_STORAGE_PATH
groups:
  "assistant_tools.groups.assistant_tools_group:AssistantToolsGroup":
    name: tools
    description: "Enhanced capabilities for AI assistants"
    config:
      search_provider: "default"
      max_file_size_mb: 50
      storage_path: "${TEMP_STORAGE_PATH:-/tmp/assistant_tools}"
      visualization_backend: "matplotlib"
      max_concurrent_requests: 5
      request_timeout_seconds: 30
```

## Installation/Deployment Guide

### 1. Installation Requirements

To install the AssistantTools ServiceGroup, you'll need:

1. Python 3.10 or higher
2. AutoMCP framework
3. Access to required APIs (search API, etc.)

### 2. Installation Steps

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/assistant-tools.git
   cd assistant-tools
   ```

2. **Set up environment:**
   ```bash
   # Using uv (recommended)
   uv venv
   source .venv/bin/activate
   uv sync
   
   # Using pip
   python -m venv .venv
   source .venv/bin/activate
   pip install -e .
   ```

3. **Configure environment variables:**
   Create a `.env` file in the project root:
   ```
   SEARCH_API_KEY=your_api_key_here
   TEMP_STORAGE_PATH=/path/to/storage
   ```

4. **Verify installation:**
   ```bash
   automcp run config/assistant_tools.yaml
   ```

### 3. Integration with AI Assistant

1. **Install using MCP CLI:**
   ```bash
   mcp install run_assistant_tools.py --name "Assistant Tools" -f .env
   ```

2. **Add to your assistant's available tools:**
   - Open the assistant configuration
   - Add the "Assistant Tools" server to the tools list
   - Ensure permissions are set correctly

3. **Usage in prompts:**
   ```
   You now have access to enhanced research capabilities through the tools.* operations.
   For example, you can search the web with tools.web_search, analyze files with tools.analyze_file, etc.
   ```

### 4. Troubleshooting

1. **API Connection Issues:**
   - Verify API keys are set correctly in environment variables
   - Check network connectivity to external services

2. **File Analysis Failures:**
   - Ensure file paths are accessible
   - Check file size limits (default 50MB max)

3. **Visualization Errors:**
   - Verify matplotlib, plotly, and other visualization dependencies are installed
   - Check if storage path is writable

## Schema Implementation

The complete schema implementation will be in `assistant_tools/schemas.py` and will include all the schema definitions shown above.

## ServiceGroup Implementation

The implementation will separate concerns into modules:

1. Main ServiceGroup: `assistant_tools/groups/assistant_tools_group.py`
2. Web Search module: `assistant_tools/services/web_search.py`
3. File Analysis module: `assistant_tools/services/file_analysis.py`
4. Repo Analysis module: `assistant_tools/services/repo_analysis.py`
5. Visualization module: `assistant_tools/services/visualization.py`
6. Document module: `assistant_tools/services/document.py`
7. Text Analysis module: `assistant_tools/services/text_analysis.py`

The main ServiceGroup will delegate to these modules for the actual implementation.