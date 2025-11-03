# LangSmith Integration for Alan's AI Assistant

## Overview

Alan's AI Assistant now includes **LangSmith tracking** for comprehensive monitoring and debugging of LangChain operations. This integration provides detailed insights into AI interactions, performance metrics, and conversation flows.

## Features

### 🔍 **Comprehensive Tracking**
- **Email Reply Generation** - Track AI-powered email responses
- **Content Evaluation** - Monitor content analysis decisions
- **RAG Operations** - Track knowledge base interactions
- **Performance Metrics** - Monitor response times and token usage

### 📊 **Rich Metadata**
- Sender information and email context
- User interests and conversation history
- RAG context and document counts
- Evaluation confidence scores
- Custom tags and project organization

### 🎯 **Project Organization**
- Separate projects for different AI operations
- Customizable project names via environment variables
- Tagged runs for easy filtering and analysis

## Setup

### 1. **Get LangSmith API Key**
1. Visit [https://smith.langchain.com/](https://smith.langchain.com/)
2. Sign up for a free account
3. Navigate to Settings → API Keys
4. Create a new API key

### 2. **Configure Environment Variables**

Add to your `.env` file:

```bash
# LangSmith Configuration
LANGSMITH_API_KEY=your-langsmith-api-key-here
LANGSMITH_PROJECT=alan-ai-assistant

# Optional: Separate projects for different operations
LANGSMITH_PROJECT_EMAIL=alan-email-replies
LANGSMITH_PROJECT_EVALUATION=alan-content-evaluation
```

### 3. **Install Dependencies**

The LangSmith dependency is already included in `requirements.txt`:

```bash
pip install -r requirements.txt
```

## Usage

### **Automatic Integration**

LangSmith tracking is **automatically enabled** when the `LANGSMITH_API_KEY` environment variable is set. No code changes required!

### **What Gets Tracked**

#### **Email Reply Generation**
- **Project**: `alan-ai-assistant` (or custom)
- **Tags**: `["email_reply", "rag_powered"]`
- **Metadata**:
  - Sender name and email
  - Email subject
  - User interests
  - Context document count
  - Conversation history length

#### **Content Evaluation**
- **Project**: `alan-content-evaluation` (or custom)
- **Tags**: `["content_evaluation", "rag_decision"]`
- **Metadata**:
  - Sender email
  - Subject
  - Content length
  - Attachment count
  - Link count
  - Evaluation type

### **Viewing Traces**

1. **Visit LangSmith Dashboard**: [https://smith.langchain.com/](https://smith.langchain.com/)
2. **Select Your Project**: Choose from your configured projects
3. **Browse Runs**: View individual AI interactions
4. **Analyze Performance**: Check response times and token usage
5. **Debug Issues**: Examine failed runs and error messages

## Configuration Options

### **Environment Variables**

| Variable | Description | Default |
|----------|-------------|---------|
| `LANGSMITH_API_KEY` | Your LangSmith API key | Required |
| `LANGSMITH_PROJECT` | Main project name | `alan-ai-assistant` |
| `LANGSMITH_PROJECT_EMAIL` | Email replies project | Uses main project |
| `LANGSMITH_PROJECT_EVALUATION` | Content evaluation project | Uses main project |

### **Custom Project Names**

You can customize project names for different operations:

```bash
# Separate projects for better organization
LANGSMITH_PROJECT=alan-main
LANGSMITH_PROJECT_EMAIL=alan-email-replies
LANGSMITH_PROJECT_EVALUATION=alan-content-evaluation
```

## Benefits

### **🔍 Debugging & Monitoring**
- **Real-time monitoring** of AI interactions
- **Error tracking** and failure analysis
- **Performance optimization** insights
- **Token usage** monitoring

### **📈 Analytics & Insights**
- **Usage patterns** analysis
- **Response quality** metrics
- **User interaction** tracking
- **RAG effectiveness** measurement

### **🛠️ Development & Testing**
- **A/B testing** different prompts
- **Model comparison** analysis
- **Prompt optimization** based on real data
- **Quality assurance** monitoring

## Troubleshooting

### **LangSmith Not Tracking**

1. **Check API Key**: Ensure `LANGSMITH_API_KEY` is set correctly
2. **Verify Project**: Check if project name is valid
3. **Check Logs**: Look for LangSmith initialization messages
4. **Test Connection**: Verify API key works in LangSmith dashboard

### **Common Issues**

#### **"LangSmith tracking disabled"**
- **Cause**: `LANGSMITH_API_KEY` not set
- **Solution**: Add API key to `.env` file

#### **"Failed to initialize LangSmith tracking"**
- **Cause**: Invalid API key or network issues
- **Solution**: Verify API key and check internet connection

#### **"Project not found"**
- **Cause**: Invalid project name
- **Solution**: Use existing project or create new one in LangSmith

## Example Logs

### **Successful Initialization**
```
INFO:ai_modules.ai_service:LangSmith tracking enabled for project: alan-ai-assistant
INFO:ai_modules.content_evaluator:LangSmith tracking enabled for content evaluation project: alan-content-evaluation
```

### **Disabled Tracking**
```
INFO:ai_modules.ai_service:LangSmith tracking disabled (LANGSMITH_API_KEY not set)
INFO:ai_modules.content_evaluator:LangSmith tracking disabled for content evaluation (LANGSMITH_API_KEY not set)
```

## Best Practices

### **🎯 Project Organization**
- Use separate projects for different AI operations
- Name projects descriptively
- Use consistent naming conventions

### **🏷️ Tagging Strategy**
- Use meaningful tags for easy filtering
- Tag by operation type (`email_reply`, `content_evaluation`)
- Tag by model version or configuration

### **📊 Metadata Usage**
- Include relevant context in metadata
- Use consistent metadata keys
- Avoid sensitive information in metadata

### **🔒 Security**
- Keep API keys secure
- Use environment variables
- Don't commit API keys to version control

## Integration Status

✅ **AI Service** - Email reply generation tracking  
✅ **Content Evaluator** - Content analysis tracking  
✅ **RAG Engine** - Knowledge base interaction tracking  
✅ **Error Handling** - Graceful fallback when disabled  
✅ **Configuration** - Environment variable based setup  
✅ **Documentation** - Comprehensive setup guide  

## Next Steps

1. **Set up LangSmith account** and get API key
2. **Configure environment variables** in `.env` file
3. **Start Alan** and begin tracking AI interactions
4. **Monitor dashboard** for insights and optimization opportunities
5. **Use data** to improve prompts and system performance

---

**LangSmith integration is now ready!** 🎉 

Start tracking your AI interactions and gain valuable insights into Alan's performance and user interactions.
