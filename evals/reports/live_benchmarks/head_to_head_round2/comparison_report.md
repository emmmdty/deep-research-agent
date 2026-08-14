# Full Comparator Comparison

> Generated at: 2026-08-15 03:36:13

## T01 2024年大语言模型Agent架构的最新进展

| Comparator | Status | Judge | Sources | Aspect | Notes |
| --- | --- | ---: | ---: | ---: | --- |
| ours_v2 | completed | 3.2 | 47 | 0.8 | - |
| odr | completed | 5.5 | 31 | 0.8 | - |
| gptr | completed | 0 | 0 | 0.4 | - |

| Pairwise vs ours | Winner | Score Diff | Reason |
| --- | --- | ---: | --- |
| odr | B | -4.6 | 报告X在深度、结构、连贯性和引用完整性上显著优于报告Y，覆盖具体框架、协议与实证数据；报告Y内容浅尝辄止、结构断裂且缺乏有效支撑。 |
| gptr | B | -4 | 报告X在深度、结构、引用质量和连贯性上均明显优于报告Y，尽管存在少量准确性瑕疵；报告Y缺乏具体分析和完整引用，整体质量较低。 |

## T02 RAG（检索增强生成）技术的原理和应用

| Comparator | Status | Judge | Sources | Aspect | Notes |
| --- | --- | ---: | ---: | ---: | --- |
| ours_v2 | completed | 4.0 | 92 | 0.8 | - |
| odr | completed | 6.0 | 23 | 1.0 | - |
| gptr | completed | 7.3 | 0 | 0.2 | - |

| Pairwise vs ours | Winner | Score Diff | Reason |
| --- | --- | ---: | --- |
| odr | B | -6.2 | 报告X在深度、结构与技术细节上远胜报告Y，报告Y仅为定义拼贴，缺乏实质内容。 |
| gptr | B | -6.0 | 报告X在深度、结构、连贯性和可追溯性上全面优于报告Y，报告Y更像未整理的笔记而非正式报告。 |

## T03 多模态大模型的发展现状与趋势

| Comparator | Status | Judge | Sources | Aspect | Notes |
| --- | --- | ---: | ---: | ---: | --- |
| ours_v2 | completed | 2.1 | 95 | 0.4 | - |
| odr | failed | - | - | - | Traceback (most recent call last):
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/scripts/run_odr_isolated.py", line 138, in <module>
    main()
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/scripts/run_odr_isolated.py", line 119, in main
    report = asyncio.run(run_research(args.topic))
  File "/usr/lib/python3.10/asyncio/runners.py", line 44, in run
    return loop.run_until_complete(main)
  File "/usr/lib/python3.10/asyncio/base_events.py", line 649, in run_until_complete
    return future.result()
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/scripts/run_odr_isolated.py", line 106, in run_research
    raise RuntimeError("open_deep_research returned an empty report")
RuntimeError: open_deep_research returned an empty report |
| gptr | completed | 7.8 | 0 | 0.4 | - |

| Pairwise vs ours | Winner | Score Diff | Reason |
| --- | --- | ---: | --- |
| odr | skipped | - | Traceback (most recent call last):
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/scripts/run_odr_isolated.py", line 138, in <module>
    main()
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/scripts/run_odr_isolated.py", line 119, in main
    report = asyncio.run(run_research(args.topic))
  File "/usr/lib/python3.10/asyncio/runners.py", line 44, in run
    return loop.run_until_complete(main)
  File "/usr/lib/python3.10/asyncio/base_events.py", line 649, in run_until_complete
    return future.result()
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/scripts/run_odr_isolated.py", line 106, in run_research
    raise RuntimeError("open_deep_research returned an empty report")
RuntimeError: open_deep_research returned an empty report |
| gptr | B | -5 | 报告X具备系统化分析和完整结构，而报告Y仅为无来源的数据堆砌，深度与连贯性均不足 |

## T04 AI Agent 在金融领域的应用案例

| Comparator | Status | Judge | Sources | Aspect | Notes |
| --- | --- | ---: | ---: | ---: | --- |
| ours_v2 | completed | 5.3 | 79 | 0.0 | - |
| odr | completed | 7.2 | 0 | 0.0 | - |
| gptr | failed | - | - | - | Traceback (most recent call last):
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/httpx/_transports/default.py", line 101, in map_httpcore_exceptions
    yield
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/httpx/_transports/default.py", line 394, in handle_async_request
    resp = await self._pool.handle_async_request(req)
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/httpcore/_async/connection_pool.py", line 256, in handle_async_request
    raise exc from None
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/httpcore/_async/connection_pool.py", line 236, in handle_async_request
    response = await connection.handle_async_request(
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/httpcore/_async/http_proxy.py", line 316, in handle_async_request
    stream = await stream.start_tls(**kwargs)
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/httpcore/_async/http11.py", line 376, in start_tls
    return await self._stream.start_tls(ssl_context, server_hostname, timeout)
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/httpcore/_backends/anyio.py", line 67, in start_tls
    with map_exceptions(exc_map):
  File "/usr/lib/python3.10/contextlib.py", line 153, in __exit__
    self.gen.throw(typ, value, traceback)
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/httpcore/_exceptions.py", line 14, in map_exceptions
    raise to_exc(exc) from exc
httpcore.ConnectError

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/openai/_base_client.py", line 1648, in request
    response = await self._send_request(
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/openai/_client.py", line 1074, in _send_request
    response = await self._send_with_auth_retry(request, stream=stream, **kwargs)
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/openai/_client.py", line 1052, in _send_with_auth_retry
    response = await super()._send_request(request, stream=stream, **kwargs)
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/openai/_base_client.py", line 1571, in _send_request
    return await self._client.send(request, stream=stream, **kwargs)
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/httpx/_client.py", line 1629, in send
    response = await self._send_handling_auth(
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/httpx/_client.py", line 1657, in _send_handling_auth
    response = await self._send_handling_redirects(
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/httpx/_client.py", line 1694, in _send_handling_redirects
    response = await self._send_single_request(request)
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/httpx/_client.py", line 1730, in _send_single_request
    response = await transport.handle_async_request(request)
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/httpx/_transports/default.py", line 393, in handle_async_request
    with map_httpcore_exceptions():
  File "/usr/lib/python3.10/contextlib.py", line 153, in __exit__
    self.gen.throw(typ, value, traceback)
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/httpx/_transports/default.py", line 118, in map_httpcore_exceptions
    raise mapped_exc(message) from exc
httpx.ConnectError

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/gpt_researcher/actions/agent_creator.py", line 27, in choose_agent
    response = await create_chat_completion(
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/gpt_researcher/utils/llm.py", line 70, in create_chat_completion
    response = await provider.get_chat_response(
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/scripts/run_gptr_isolated.py", line 91, in _get_chat_response
    output = await orig_get(self, messages, stream, websocket)
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/gpt_researcher/llm_provider/generic/base.py", line 150, in get_chat_response
    output = await self.llm.ainvoke(messages)
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/langchain_core/language_models/chat_models.py", line 417, in ainvoke
    llm_result = await self.agenerate_prompt(
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/langchain_core/language_models/chat_models.py", line 1036, in agenerate_prompt
    return await self.agenerate(
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/langchain_core/language_models/chat_models.py", line 994, in agenerate
    raise exceptions[0]
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/langchain_core/language_models/chat_models.py", line 1164, in _agenerate_with_cache
    result = await self._agenerate(
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/langchain_openai/chat_models/base.py", line 1456, in _agenerate
    raise e
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/langchain_openai/chat_models/base.py", line 1449, in _agenerate
    raw_response = await self.async_client.with_raw_response.create(
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/openai/_legacy_response.py", line 384, in wrapped
    return cast(LegacyAPIResponse[R], await func(*args, **kwargs))
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/scripts/run_gptr_isolated.py", line 81, in _async
    return await orig_async(self, **_inject_extra(kwargs))
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/openai/resources/chat/completions/completions.py", line 2877, in create
    return await self._post(
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/openai/_base_client.py", line 1931, in post
    return await self.request(cast_to, opts, stream=stream, stream_cls=stream_cls)
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/openai/_base_client.py", line 1683, in request
    raise APIConnectionError(request=request) from err
openai.APIConnectionError: Connection error.

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/scripts/run_gptr_isolated.py", line 138, in main
    report = asyncio.run(run_research(args.topic))
  File "/usr/lib/python3.10/asyncio/runners.py", line 44, in run
    return loop.run_until_complete(main)
  File "/usr/lib/python3.10/asyncio/base_events.py", line 649, in run_until_complete
    return future.result()
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/scripts/run_gptr_isolated.py", line 113, in run_research
    await researcher.conduct_research()
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/gpt_researcher/agent.py", line 133, in conduct_research
    self.agent, self.role = await choose_agent(
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/gpt_researcher/actions/agent_creator.py", line 43, in choose_agent
    return await handle_json_error(response)
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/gpt_researcher/actions/agent_creator.py", line 55, in handle_json_error
    json_string = extract_json_with_regex(response)
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/gpt_researcher/actions/agent_creator.py", line 71, in extract_json_with_regex
    json_match = re.search(r"{.*?}", response, re.DOTALL)
  File "/usr/lib/python3.10/re.py", line 200, in search
    return _compile(pattern, flags).search(string)
TypeError: expected string or bytes-like object |

| Pairwise vs ours | Winner | Score Diff | Reason |
| --- | --- | ---: | --- |
| odr | B | -3 | 报告X在研究深度、准确性、连贯性、引用质量和结构完整性上全面领先，提供了具体可验证的案例与数据，而报告Y多为宏观列点和摘要，缺乏系统性与精确性。 |
| gptr | skipped | - | Traceback (most recent call last):
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/httpx/_transports/default.py", line 101, in map_httpcore_exceptions
    yield
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/httpx/_transports/default.py", line 394, in handle_async_request
    resp = await self._pool.handle_async_request(req)
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/httpcore/_async/connection_pool.py", line 256, in handle_async_request
    raise exc from None
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/httpcore/_async/connection_pool.py", line 236, in handle_async_request
    response = await connection.handle_async_request(
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/httpcore/_async/http_proxy.py", line 316, in handle_async_request
    stream = await stream.start_tls(**kwargs)
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/httpcore/_async/http11.py", line 376, in start_tls
    return await self._stream.start_tls(ssl_context, server_hostname, timeout)
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/httpcore/_backends/anyio.py", line 67, in start_tls
    with map_exceptions(exc_map):
  File "/usr/lib/python3.10/contextlib.py", line 153, in __exit__
    self.gen.throw(typ, value, traceback)
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/httpcore/_exceptions.py", line 14, in map_exceptions
    raise to_exc(exc) from exc
httpcore.ConnectError

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/openai/_base_client.py", line 1648, in request
    response = await self._send_request(
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/openai/_client.py", line 1074, in _send_request
    response = await self._send_with_auth_retry(request, stream=stream, **kwargs)
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/openai/_client.py", line 1052, in _send_with_auth_retry
    response = await super()._send_request(request, stream=stream, **kwargs)
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/openai/_base_client.py", line 1571, in _send_request
    return await self._client.send(request, stream=stream, **kwargs)
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/httpx/_client.py", line 1629, in send
    response = await self._send_handling_auth(
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/httpx/_client.py", line 1657, in _send_handling_auth
    response = await self._send_handling_redirects(
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/httpx/_client.py", line 1694, in _send_handling_redirects
    response = await self._send_single_request(request)
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/httpx/_client.py", line 1730, in _send_single_request
    response = await transport.handle_async_request(request)
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/httpx/_transports/default.py", line 393, in handle_async_request
    with map_httpcore_exceptions():
  File "/usr/lib/python3.10/contextlib.py", line 153, in __exit__
    self.gen.throw(typ, value, traceback)
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/httpx/_transports/default.py", line 118, in map_httpcore_exceptions
    raise mapped_exc(message) from exc
httpx.ConnectError

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/gpt_researcher/actions/agent_creator.py", line 27, in choose_agent
    response = await create_chat_completion(
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/gpt_researcher/utils/llm.py", line 70, in create_chat_completion
    response = await provider.get_chat_response(
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/scripts/run_gptr_isolated.py", line 91, in _get_chat_response
    output = await orig_get(self, messages, stream, websocket)
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/gpt_researcher/llm_provider/generic/base.py", line 150, in get_chat_response
    output = await self.llm.ainvoke(messages)
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/langchain_core/language_models/chat_models.py", line 417, in ainvoke
    llm_result = await self.agenerate_prompt(
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/langchain_core/language_models/chat_models.py", line 1036, in agenerate_prompt
    return await self.agenerate(
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/langchain_core/language_models/chat_models.py", line 994, in agenerate
    raise exceptions[0]
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/langchain_core/language_models/chat_models.py", line 1164, in _agenerate_with_cache
    result = await self._agenerate(
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/langchain_openai/chat_models/base.py", line 1456, in _agenerate
    raise e
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/langchain_openai/chat_models/base.py", line 1449, in _agenerate
    raw_response = await self.async_client.with_raw_response.create(
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/openai/_legacy_response.py", line 384, in wrapped
    return cast(LegacyAPIResponse[R], await func(*args, **kwargs))
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/scripts/run_gptr_isolated.py", line 81, in _async
    return await orig_async(self, **_inject_extra(kwargs))
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/openai/resources/chat/completions/completions.py", line 2877, in create
    return await self._post(
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/openai/_base_client.py", line 1931, in post
    return await self.request(cast_to, opts, stream=stream, stream_cls=stream_cls)
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/openai/_base_client.py", line 1683, in request
    raise APIConnectionError(request=request) from err
openai.APIConnectionError: Connection error.

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/scripts/run_gptr_isolated.py", line 138, in main
    report = asyncio.run(run_research(args.topic))
  File "/usr/lib/python3.10/asyncio/runners.py", line 44, in run
    return loop.run_until_complete(main)
  File "/usr/lib/python3.10/asyncio/base_events.py", line 649, in run_until_complete
    return future.result()
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/scripts/run_gptr_isolated.py", line 113, in run_research
    await researcher.conduct_research()
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/gpt_researcher/agent.py", line 133, in conduct_research
    self.agent, self.role = await choose_agent(
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/gpt_researcher/actions/agent_creator.py", line 43, in choose_agent
    return await handle_json_error(response)
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/gpt_researcher/actions/agent_creator.py", line 55, in handle_json_error
    json_string = extract_json_with_regex(response)
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv/lib/python3.10/site-packages/gpt_researcher/actions/agent_creator.py", line 71, in extract_json_with_regex
    json_match = re.search(r"{.*?}", response, re.DOTALL)
  File "/usr/lib/python3.10/re.py", line 200, in search
    return _compile(pattern, flags).search(string)
TypeError: expected string or bytes-like object |

## T05 开源 LLM 与闭源 LLM 的性能对比

| Comparator | Status | Judge | Sources | Aspect | Notes |
| --- | --- | ---: | ---: | ---: | --- |
| ours_v2 | failed | - | - | - | 2026-08-15 03:30:22.538 | WARNING  | deep_research_agent.agents.llm:chat:289 - LLM call attempt 1 failed: Connection error.
2026-08-15 03:30:24.545 | WARNING  | deep_research_agent.agents.llm:chat:289 - LLM call attempt 2 failed: Connection error.
2026-08-15 03:30:26.546 | WARNING  | deep_research_agent.agents.llm:chat:289 - LLM call attempt 3 failed: Connection error.
2026-08-15 03:30:26.547 | WARNING  | deep_research_agent.agents.planner:_model_objectives:118 - LLM planning failed; using deterministic planner: LLM call failed after 3 attempts: Connection error.
2026-08-15 03:30:29.004 | WARNING  | deep_research_agent.agents.llm:tool_loop:422 - LLM tool loop round 1 failed: Connection error.
2026-08-15 03:30:29.005 | WARNING  | deep_research_agent.agents.researcher:_maybe_tool_loop:267 - researcher: function-calling round unavailable (LLM tool loop failed after 1 attempts: Connection error.); falling back
2026-08-15 03:30:29.095 | WARNING  | deep_research_agent.agents.llm:tool_loop:422 - LLM tool loop round 1 failed: Connection error.
2026-08-15 03:30:29.095 | WARNING  | deep_research_agent.agents.researcher:_maybe_tool_loop:267 - researcher: function-calling round unavailable (LLM tool loop failed after 1 attempts: Connection error.); falling back
2026-08-15 03:30:29.110 | WARNING  | deep_research_agent.agents.llm:tool_loop:422 - LLM tool loop round 1 failed: Connection error.
2026-08-15 03:30:29.110 | WARNING  | deep_research_agent.agents.researcher:_maybe_tool_loop:267 - researcher: function-calling round unavailable (LLM tool loop failed after 1 attempts: Connection error.); falling back
2026-08-15 03:30:31.405 | WARNING  | deep_research_agent.agents.llm:chat:289 - LLM call attempt 1 failed: Connection error.
2026-08-15 03:30:31.421 | WARNING  | deep_research_agent.agents.llm:chat:289 - LLM call attempt 1 failed: Connection error.
2026-08-15 03:30:31.565 | WARNING  | deep_research_agent.agents.llm:chat:289 - LLM call attempt 1 failed: Connection error.
2026-08-15 03:30:33.487 | WARNING  | deep_research_agent.agents.llm:chat:289 - LLM call attempt 2 failed: Connection error.
2026-08-15 03:30:33.679 | WARNING  | deep_research_agent.agents.llm:chat:289 - LLM call attempt 2 failed: Connection error.
2026-08-15 03:30:35.821 | WARNING  | deep_research_agent.agents.llm:chat:289 - LLM call attempt 3 failed: Connection error.
2026-08-15 03:30:35.821 | WARNING  | deep_research_agent.agents.researcher:_agentic_plan_queries:419 - researcher research-01-which-event-representations-measurab: query planning unavailable (LLM call failed after 3 attempts: Connection error.); using the task objective verbatim
2026-08-15 03:30:35.865 | WARNING  | deep_research_agent.agents.llm:chat:289 - LLM call attempt 3 failed: Connection error.
2026-08-15 03:30:35.865 | WARNING  | deep_research_agent.agents.researcher:_agentic_plan_queries:419 - researcher research-02-which-benchmarks-isolate-gains-from-: query planning unavailable (LLM call failed after 3 attempts: Connection error.); using the task objective verbatim
2026-08-15 03:30:36.142 | WARNING  | deep_research_agent.connectors.tools.web_search:_search_tavily:89 - Tavily 搜索失败: HTTPSConnectionPool(host='api.tavily.com', port=443): Max retries exceeded with url: /search (Caused by SSLError(SSLEOFError(8, '[SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol (_ssl.c:1007)')))，回退到 DuckDuckGo
2026-08-15 03:30:36.209 | WARNING  | deep_research_agent.connectors.tools.web_search:_search_tavily:89 - Tavily 搜索失败: HTTPSConnectionPool(host='api.tavily.com', port=443): Max retries exceeded with url: /search (Caused by SSLError(SSLEOFError(8, '[SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol (_ssl.c:1007)')))，回退到 DuckDuckGo
2026-08-15 03:30:37.279 | WARNING  | deep_research_agent.connectors.tools.web_search:_search_duckduckgo:126 - DuckDuckGo 搜索第 1 次失败: ConnectError: ConnectError('error sending request for url (https://html.duckduckgo.com/html/)', 'https://html.duckduckgo.com/html/')
2026-08-15 03:30:37.295 | WARNING  | deep_research_agent.connectors.tools.web_search:_search_duckduckgo:126 - DuckDuckGo 搜索第 1 次失败: ConnectError: ConnectError('error sending request for url (https://html.duckduckgo.com/html/)', 'https://html.duckduckgo.com/html/')
2026-08-15 03:30:38.599 | WARNING  | deep_research_agent.connectors.tools.web_search:_search_duckduckgo:126 - DuckDuckGo 搜索第 2 次失败: ConnectError: ConnectError('error sending request for url (https://search.yahoo.com/search;_ylt=v9wMH1bFOt0Hde703l957u5t;_ylu=bAR0R_0Gyt8ulWKTBi0fGuDob36bh1fkdpqo_Y2RnROOXys?p=Which+benchmarks+isolate+gains+from+the+representation+rather+than+the+base+model%3F)', 'https://search.yahoo.com/search;_ylt=v9wMH1bFOt0Hde703l957u5t;_ylu=bAR0R_0Gyt8ulWKTBi0fGuDob36bh1fkdpqo_Y2RnROOXys?p=Which+benchmarks+isolate+gains+from+the+representation+rather+than+the+base+model%3F')
2026-08-15 03:30:39.166 | WARNING  | deep_research_agent.connectors.tools.web_search:_search_duckduckgo:126 - DuckDuckGo 搜索第 2 次失败: ConnectError: ConnectError('error sending request for url (https://yandex.com/search/site/?text=Which+event+representations+measurably+improve+planning%2C+memory%2C+or+tool+use%3F&web=1&searchid=5592869)', 'https://yandex.com/search/site/?text=Which+event+representations+measurably+improve+planning%2C+memory%2C+or+tool+use%3F&web=1&searchid=5592869')
2026-08-15 03:30:40.153 | WARNING  | deep_research_agent.connectors.tools.web_search:_search_duckduckgo:126 - DuckDuckGo 搜索第 3 次失败: ConnectError: ConnectError('error sending request for url (https://yandex.com/search/site/?text=Which+event+representations+measurably+improve+planning%2C+memory%2C+or+tool+use%3F&web=1&searchid=8369870)', 'https://yandex.com/search/site/?text=Which+event+representations+measurably+improve+planning%2C+memory%2C+or+tool+use%3F&web=1&searchid=8369870')
2026-08-15 03:30:40.154 | ERROR    | deep_research_agent.connectors.tools.web_search:_search_duckduckgo:128 - DuckDuckGo 搜索失败: ConnectError: ConnectError('error sending request for url (https://yandex.com/search/site/?text=Which+event+representations+measurably+improve+planning%2C+memory%2C+or+tool+use%3F&web=1&searchid=8369870)', 'https://yandex.com/search/site/?text=Which+event+representations+measurably+improve+planning%2C+memory%2C+or+tool+use%3F&web=1&searchid=8369870')
2026-08-15 03:30:40.154 | WARNING  | deep_research_agent.connectors.tools.web_search:_search_duckduckgo:126 - DuckDuckGo 搜索第 3 次失败: ConnectError: ConnectError('error sending request for url (https://search.yahoo.com/search;_ylt=ElzU2FvUYODi-ZK0HGURzjrA;_ylu=U-IY2ezrfV8Xqd-RRK0CgXyh6GvGvuubfpOx0cV1HxhhTtw?p=Which+benchmarks+isolate+gains+from+the+representation+rather+than+the+base+model%3F)', 'https://search.yahoo.com/search;_ylt=ElzU2FvUYODi-ZK0HGURzjrA;_ylu=U-IY2ezrfV8Xqd-RRK0CgXyh6GvGvuubfpOx0cV1HxhhTtw?p=Which+benchmarks+isolate+gains+from+the+representation+rather+than+the+base+model%3F')
2026-08-15 03:30:40.154 | ERROR    | deep_research_agent.connectors.tools.web_search:_search_duckduckgo:128 - DuckDuckGo 搜索失败: ConnectError: ConnectError('error sending request for url (https://search.yahoo.com/search;_ylt=ElzU2FvUYODi-ZK0HGURzjrA;_ylu=U-IY2ezrfV8Xqd-RRK0CgXyh6GvGvuubfpOx0cV1HxhhTtw?p=Which+benchmarks+isolate+gains+from+the+representation+rather+than+the+base+model%3F)', 'https://search.yahoo.com/search;_ylt=ElzU2FvUYODi-ZK0HGURzjrA;_ylu=U-IY2ezrfV8Xqd-RRK0CgXyh6GvGvuubfpOx0cV1HxhhTtw?p=Which+benchmarks+isolate+gains+from+the+representation+rather+than+the+base+model%3F')
2026-08-15 03:30:42.539 | WARNING  | deep_research_agent.agents.llm:tool_loop:422 - LLM tool loop round 1 failed: Connection error.
2026-08-15 03:30:42.539 | WARNING  | deep_research_agent.agents.researcher:_maybe_tool_loop:267 - researcher: function-calling round unavailable (LLM tool loop failed after 1 attempts: Connection error.); falling back
2026-08-15 03:30:42.721 | WARNING  | deep_research_agent.agents.llm:tool_loop:422 - LLM tool loop round 1 failed: Connection error.
2026-08-15 03:30:42.721 | WARNING  | deep_research_agent.agents.researcher:_maybe_tool_loop:267 - researcher: function-calling round unavailable (LLM tool loop failed after 1 attempts: Connection error.); falling back
2026-08-15 03:30:44.602 | WARNING  | deep_research_agent.agents.llm:chat:289 - LLM call attempt 1 failed: Connection error.
2026-08-15 03:30:46.709 | WARNING  | deep_research_agent.agents.llm:chat:289 - LLM call attempt 2 failed: Connection error.
2026-08-15 03:30:48.569 | WARNING  | deep_research_agent.agents.llm:chat:289 - LLM call attempt 2 failed: Connection error.
2026-08-15 03:30:48.805 | WARNING  | deep_research_agent.agents.llm:chat:289 - LLM call attempt 3 failed: Connection error.
2026-08-15 03:30:48.805 | WARNING  | deep_research_agent.agents.researcher:_agentic_plan_queries:419 - researcher research-02-which-benchmarks-isolate-gains-from-: query planning unavailable (LLM call failed after 3 attempts: Connection error.); using the task objective verbatim
2026-08-15 03:30:50.791 | WARNING  | deep_research_agent.agents.llm:chat:289 - LLM call attempt 3 failed: Connection error.
2026-08-15 03:30:50.791 | WARNING  | deep_research_agent.agents.researcher:_agentic_plan_queries:419 - researcher research-03-where-do-reported-interactions-remai: query planning unavailable (LLM call failed after 3 attempts: Connection error.); using the task objective verbatim
2026-08-15 03:30:51.043 | WARNING  | deep_research_agent.connectors.tools.web_search:_search_tavily:89 - Tavily 搜索失败: HTTPSConnectionPool(host='api.tavily.com', port=443): Max retries exceeded with url: /search (Caused by SSLError(SSLEOFError(8, '[SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol (_ssl.c:1007)')))，回退到 DuckDuckGo
2026-08-15 03:30:52.101 | WARNING  | deep_research_agent.connectors.tools.web_search:_search_duckduckgo:126 - DuckDuckGo 搜索第 1 次失败: ConnectError: ConnectError('error sending request for url (https://search.brave.com/search?q=Where+do+reported+interactions+remain+unsupported+or+contradictory%3F&source=web)', 'https://search.brave.com/search?q=Where+do+reported+interactions+remain+unsupported+or+contradictory%3F&source=web')
2026-08-15 03:30:53.930 | WARNING  | deep_research_agent.connectors.tools.web_search:_search_duckduckgo:126 - DuckDuckGo 搜索第 2 次失败: ConnectError: ConnectError('error sending request for url (https://html.duckduckgo.com/html/)', 'https://html.duckduckgo.com/html/')
2026-08-15 03:30:55.023 | WARNING  | deep_research_agent.connectors.tools.web_search:_search_duckduckgo:126 - DuckDuckGo 搜索第 3 次失败: ConnectError: ConnectError('error sending request for url (https://html.duckduckgo.com/html/)', 'https://html.duckduckgo.com/html/')
2026-08-15 03:30:55.023 | ERROR    | deep_research_agent.connectors.tools.web_search:_search_duckduckgo:128 - DuckDuckGo 搜索失败: ConnectError: ConnectError('error sending request for url (https://html.duckduckgo.com/html/)', 'https://html.duckduckgo.com/html/')
2026-08-15 03:30:57.600 | WARNING  | deep_research_agent.agents.llm:tool_loop:422 - LLM tool loop round 1 failed: Connection error.
2026-08-15 03:30:57.600 | WARNING  | deep_research_agent.agents.researcher:_maybe_tool_loop:267 - researcher: function-calling round unavailable (LLM tool loop failed after 1 attempts: Connection error.); falling back
2026-08-15 03:30:59.843 | WARNING  | deep_research_agent.agents.llm:chat:289 - LLM call attempt 1 failed: Connection error.
2026-08-15 03:30:59.971 | WARNING  | deep_research_agent.agents.llm:chat:289 - LLM call attempt 1 failed: Connection error.
2026-08-15 03:31:01.826 | WARNING  | deep_research_agent.agents.llm:chat:289 - LLM call attempt 2 failed: Connection error.
2026-08-15 03:31:04.084 | WARNING  | deep_research_agent.agents.llm:chat:289 - LLM call attempt 3 failed: Connection error.
2026-08-15 03:31:04.084 | WARNING  | deep_research_agent.agents.researcher:_agentic_plan_queries:419 - researcher research-01-which-event-representations-measurab: query planning unavailable (LLM call failed after 3 attempts: Connection error.); using the task objective verbatim
2026-08-15 03:31:17.171 | WARNING  | deep_research_agent.agents.llm:chat:289 - LLM call attempt 2 failed: Connection error.
2026-08-15 03:31:19.345 | WARNING  | deep_research_agent.agents.llm:chat:289 - LLM call attempt 3 failed: Connection error.
2026-08-15 03:31:19.345 | WARNING  | deep_research_agent.agents.researcher:_agentic_plan_queries:419 - researcher research-03-where-do-reported-interactions-remai: query planning unavailable (LLM call failed after 3 attempts: Connection error.); using the task objective verbatim
Traceback (most recent call last):
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/scripts/run_ours_v2_isolated.py", line 195, in <module>
    main()
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/scripts/run_ours_v2_isolated.py", line 184, in main
    report, meta = asyncio.run(_run(args.topic))
  File "/usr/lib/python3.10/asyncio/runners.py", line 44, in run
    return loop.run_until_complete(main)
  File "/usr/lib/python3.10/asyncio/base_events.py", line 649, in run_until_complete
    return future.result()
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/scripts/run_ours_v2_isolated.py", line 92, in _run
    raise RuntimeError(f"scheduler-v2 job {job_id} produced no report")
RuntimeError: scheduler-v2 job 20260814T193020Z-24a9c0e5 produced no report |
| odr | failed | - | - | - | Traceback (most recent call last):
  File "/tmp/odr-venv/lib/python3.10/site-packages/httpx2/_transports/default.py", line 98, in map_httpcore_exceptions
    yield
  File "/tmp/odr-venv/lib/python3.10/site-packages/httpx2/_transports/default.py", line 388, in handle_async_request
    resp = await self._pool.handle_async_request(req)
  File "/tmp/odr-venv/lib/python3.10/site-packages/httpcore2/_async/connection_pool.py", line 242, in handle_async_request
    raise exc from None
  File "/tmp/odr-venv/lib/python3.10/site-packages/httpcore2/_async/connection_pool.py", line 224, in handle_async_request
    response = await connection.handle_async_request(pool_request.request)
  File "/tmp/odr-venv/lib/python3.10/site-packages/httpcore2/_async/http_proxy.py", line 301, in handle_async_request
    stream = await stream.start_tls(**kwargs)
  File "/tmp/odr-venv/lib/python3.10/site-packages/httpcore2/_async/http11.py", line 354, in start_tls
    return await self._stream.start_tls(ssl_context, server_hostname, timeout)
  File "/tmp/odr-venv/lib/python3.10/site-packages/httpcore2/_backends/anyio.py", line 69, in start_tls
    with map_exceptions(exc_map):
  File "/usr/lib/python3.10/contextlib.py", line 153, in __exit__
    self.gen.throw(typ, value, traceback)
  File "/tmp/odr-venv/lib/python3.10/site-packages/httpcore2/_exceptions.py", line 17, in map_exceptions
    raise to_exc(exc) from exc
httpcore2.ConnectError

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/tmp/odr-venv/lib/python3.10/site-packages/openai/_base_client.py", line 1713, in request
    response = await self._send_request(
  File "/tmp/odr-venv/lib/python3.10/site-packages/openai/_client.py", line 1097, in _send_request
    response = await self._send_with_auth_retry(request, stream=stream, **kwargs)
  File "/tmp/odr-venv/lib/python3.10/site-packages/openai/_client.py", line 1075, in _send_with_auth_retry
    response = await super()._send_request(request, stream=stream, **kwargs)
  File "/tmp/odr-venv/lib/python3.10/site-packages/openai/_base_client.py", line 1632, in _send_request
    return await self._client.send(request, stream=stream, **kwargs)
  File "/tmp/odr-venv/lib/python3.10/site-packages/httpx2/_client.py", line 1825, in send
    response = await self._send_handling_auth(
  File "/tmp/odr-venv/lib/python3.10/site-packages/httpx2/_client.py", line 1853, in _send_handling_auth
    response = await self._send_handling_redirects(
  File "/tmp/odr-venv/lib/python3.10/site-packages/httpx2/_client.py", line 1888, in _send_handling_redirects
    response = await self._send_single_request(request)
  File "/tmp/odr-venv/lib/python3.10/site-packages/httpx2/_client.py", line 1922, in _send_single_request
    response = await transport.handle_async_request(request)
  File "/tmp/odr-venv/lib/python3.10/site-packages/httpx2/_transports/default.py", line 387, in handle_async_request
    with map_httpcore_exceptions():
  File "/usr/lib/python3.10/contextlib.py", line 153, in __exit__
    self.gen.throw(typ, value, traceback)
  File "/tmp/odr-venv/lib/python3.10/site-packages/httpx2/_transports/default.py", line 115, in map_httpcore_exceptions
    raise mapped_exc(message) from exc
httpx2.ConnectError

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/scripts/run_odr_isolated.py", line 138, in <module>
    main()
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/scripts/run_odr_isolated.py", line 119, in main
    report = asyncio.run(run_research(args.topic))
  File "/usr/lib/python3.10/asyncio/runners.py", line 44, in run
    return loop.run_until_complete(main)
  File "/usr/lib/python3.10/asyncio/base_events.py", line 649, in run_until_complete
    return future.result()
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/scripts/run_odr_isolated.py", line 90, in run_research
    result = await deep_researcher.ainvoke(
  File "/tmp/odr-venv/lib/python3.10/site-packages/langgraph/pregel/main.py", line 4090, in ainvoke
    async for chunk in self.astream(
  File "/tmp/odr-venv/lib/python3.10/site-packages/langgraph/pregel/main.py", line 3440, in astream
    async for _ in runner.atick(
  File "/tmp/odr-venv/lib/python3.10/site-packages/langgraph/pregel/_runner.py", line 396, in atick
    await arun_with_retry(
  File "/tmp/odr-venv/lib/python3.10/site-packages/langgraph/pregel/_retry.py", line 744, in arun_with_retry
    return await task.proc.ainvoke(task.input, config)
  File "/tmp/odr-venv/lib/python3.10/site-packages/langgraph/_internal/_runnable.py", line 760, in ainvoke
    input = await step.ainvoke(input, config, **kwargs)
  File "/tmp/odr-venv/lib/python3.10/site-packages/langgraph/_internal/_runnable.py", line 522, in ainvoke
    ret = await self.afunc(*args, **kwargs)
  File "/tmp/odr-venv/lib/python3.10/site-packages/open_deep_research/deep_researcher.py", line 60, in clarify_with_user
    response = await model.ainvoke([HumanMessage(content=clarify_with_user_instructions.format(messages=get_buffer_string(messages), date=get_today_str()))])
  File "/tmp/odr-venv/lib/python3.10/site-packages/langchain_core/runnables/base.py", line 6015, in ainvoke
    return await self.bound.ainvoke(
  File "/tmp/odr-venv/lib/python3.10/site-packages/langchain_core/runnables/retry.py", line 225, in ainvoke
    return await self._acall_with_config(self._ainvoke, input, config, **kwargs)
  File "/tmp/odr-venv/lib/python3.10/site-packages/langchain_core/runnables/base.py", line 2340, in _acall_with_config
    output: Output = await coro_with_context(coro, context)
  File "/tmp/odr-venv/lib/python3.10/site-packages/langchain_core/runnables/retry.py", line 210, in _ainvoke
    async for attempt in self._async_retrying(reraise=True):
  File "/tmp/odr-venv/lib/python3.10/site-packages/tenacity/asyncio/__init__.py", line 170, in __anext__
    do = await self.iter(retry_state=self._retry_state)
  File "/tmp/odr-venv/lib/python3.10/site-packages/tenacity/asyncio/__init__.py", line 157, in iter
    result = await action(retry_state)
  File "/tmp/odr-venv/lib/python3.10/site-packages/tenacity/_utils.py", line 111, in inner
    return call(*args, **kwargs)
  File "/tmp/odr-venv/lib/python3.10/site-packages/tenacity/__init__.py", line 413, in exc_check
    raise retry_exc.reraise()
  File "/tmp/odr-venv/lib/python3.10/site-packages/tenacity/__init__.py", line 184, in reraise
    raise self.last_attempt.result()
  File "/usr/lib/python3.10/concurrent/futures/_base.py", line 451, in result
    return self.__get_result()
  File "/usr/lib/python3.10/concurrent/futures/_base.py", line 403, in __get_result
    raise self._exception
  File "/tmp/odr-venv/lib/python3.10/site-packages/langchain_core/runnables/retry.py", line 212, in _ainvoke
    result = await super().ainvoke(
  File "/tmp/odr-venv/lib/python3.10/site-packages/langchain_core/runnables/base.py", line 6015, in ainvoke
    return await self.bound.ainvoke(
  File "/tmp/odr-venv/lib/python3.10/site-packages/langchain/chat_models/base.py", line 787, in ainvoke
    return await self._model(config).ainvoke(input, config=config, **kwargs)
  File "/tmp/odr-venv/lib/python3.10/site-packages/langchain_core/runnables/base.py", line 3484, in ainvoke
    input_ = await coro_with_context(part(), context, create_task=True)
  File "/tmp/odr-venv/lib/python3.10/site-packages/langchain_core/runnables/base.py", line 6015, in ainvoke
    return await self.bound.ainvoke(
  File "/tmp/odr-venv/lib/python3.10/site-packages/langchain_core/language_models/chat_models.py", line 499, in ainvoke
    llm_result = await self.agenerate_prompt(
  File "/tmp/odr-venv/lib/python3.10/site-packages/langchain_core/language_models/chat_models.py", line 1876, in agenerate_prompt
    return await self.agenerate(
  File "/tmp/odr-venv/lib/python3.10/site-packages/langchain_core/language_models/chat_models.py", line 1834, in agenerate
    raise exceptions[0]
  File "/tmp/odr-venv/lib/python3.10/site-packages/langchain_core/language_models/chat_models.py", line 2167, in _agenerate_with_cache
    result = await self._agenerate(
  File "/tmp/odr-venv/lib/python3.10/site-packages/langchain_openai/chat_models/base.py", line 2023, in _agenerate
    _handle_openai_api_error(e)
  File "/tmp/odr-venv/lib/python3.10/site-packages/langchain_openai/chat_models/base.py", line 2016, in _agenerate
    raw_response = await self.async_client.with_raw_response.create(
  File "/tmp/odr-venv/lib/python3.10/site-packages/openai/_legacy_response.py", line 386, in wrapped
    return cast(LegacyAPIResponse[R], await func(*args, **kwargs))
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/scripts/run_odr_isolated.py", line 81, in _async_create_with_thinking_off
    return await _orig_async_create(self, **_with_thinking_off(kwargs))
  File "/tmp/odr-venv/lib/python3.10/site-packages/openai/resources/chat/completions/completions.py", line 2907, in create
    return await self._post(
  File "/tmp/odr-venv/lib/python3.10/site-packages/openai/_base_client.py", line 1996, in post
    return await self.request(cast_to, opts, stream=stream, stream_cls=stream_cls)
  File "/tmp/odr-venv/lib/python3.10/site-packages/openai/_base_client.py", line 1748, in request
    raise APIConnectionError(request=request) from err
openai.APIConnectionError: Connection error. |
| gptr | completed | 4.9 | 0 | 0.4 | - |

| Pairwise vs ours | Winner | Score Diff | Reason |
| --- | --- | ---: | --- |
| odr | skipped | - | Traceback (most recent call last):
  File "/tmp/odr-venv/lib/python3.10/site-packages/httpx2/_transports/default.py", line 98, in map_httpcore_exceptions
    yield
  File "/tmp/odr-venv/lib/python3.10/site-packages/httpx2/_transports/default.py", line 388, in handle_async_request
    resp = await self._pool.handle_async_request(req)
  File "/tmp/odr-venv/lib/python3.10/site-packages/httpcore2/_async/connection_pool.py", line 242, in handle_async_request
    raise exc from None
  File "/tmp/odr-venv/lib/python3.10/site-packages/httpcore2/_async/connection_pool.py", line 224, in handle_async_request
    response = await connection.handle_async_request(pool_request.request)
  File "/tmp/odr-venv/lib/python3.10/site-packages/httpcore2/_async/http_proxy.py", line 301, in handle_async_request
    stream = await stream.start_tls(**kwargs)
  File "/tmp/odr-venv/lib/python3.10/site-packages/httpcore2/_async/http11.py", line 354, in start_tls
    return await self._stream.start_tls(ssl_context, server_hostname, timeout)
  File "/tmp/odr-venv/lib/python3.10/site-packages/httpcore2/_backends/anyio.py", line 69, in start_tls
    with map_exceptions(exc_map):
  File "/usr/lib/python3.10/contextlib.py", line 153, in __exit__
    self.gen.throw(typ, value, traceback)
  File "/tmp/odr-venv/lib/python3.10/site-packages/httpcore2/_exceptions.py", line 17, in map_exceptions
    raise to_exc(exc) from exc
httpcore2.ConnectError

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/tmp/odr-venv/lib/python3.10/site-packages/openai/_base_client.py", line 1713, in request
    response = await self._send_request(
  File "/tmp/odr-venv/lib/python3.10/site-packages/openai/_client.py", line 1097, in _send_request
    response = await self._send_with_auth_retry(request, stream=stream, **kwargs)
  File "/tmp/odr-venv/lib/python3.10/site-packages/openai/_client.py", line 1075, in _send_with_auth_retry
    response = await super()._send_request(request, stream=stream, **kwargs)
  File "/tmp/odr-venv/lib/python3.10/site-packages/openai/_base_client.py", line 1632, in _send_request
    return await self._client.send(request, stream=stream, **kwargs)
  File "/tmp/odr-venv/lib/python3.10/site-packages/httpx2/_client.py", line 1825, in send
    response = await self._send_handling_auth(
  File "/tmp/odr-venv/lib/python3.10/site-packages/httpx2/_client.py", line 1853, in _send_handling_auth
    response = await self._send_handling_redirects(
  File "/tmp/odr-venv/lib/python3.10/site-packages/httpx2/_client.py", line 1888, in _send_handling_redirects
    response = await self._send_single_request(request)
  File "/tmp/odr-venv/lib/python3.10/site-packages/httpx2/_client.py", line 1922, in _send_single_request
    response = await transport.handle_async_request(request)
  File "/tmp/odr-venv/lib/python3.10/site-packages/httpx2/_transports/default.py", line 387, in handle_async_request
    with map_httpcore_exceptions():
  File "/usr/lib/python3.10/contextlib.py", line 153, in __exit__
    self.gen.throw(typ, value, traceback)
  File "/tmp/odr-venv/lib/python3.10/site-packages/httpx2/_transports/default.py", line 115, in map_httpcore_exceptions
    raise mapped_exc(message) from exc
httpx2.ConnectError

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/scripts/run_odr_isolated.py", line 138, in <module>
    main()
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/scripts/run_odr_isolated.py", line 119, in main
    report = asyncio.run(run_research(args.topic))
  File "/usr/lib/python3.10/asyncio/runners.py", line 44, in run
    return loop.run_until_complete(main)
  File "/usr/lib/python3.10/asyncio/base_events.py", line 649, in run_until_complete
    return future.result()
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/scripts/run_odr_isolated.py", line 90, in run_research
    result = await deep_researcher.ainvoke(
  File "/tmp/odr-venv/lib/python3.10/site-packages/langgraph/pregel/main.py", line 4090, in ainvoke
    async for chunk in self.astream(
  File "/tmp/odr-venv/lib/python3.10/site-packages/langgraph/pregel/main.py", line 3440, in astream
    async for _ in runner.atick(
  File "/tmp/odr-venv/lib/python3.10/site-packages/langgraph/pregel/_runner.py", line 396, in atick
    await arun_with_retry(
  File "/tmp/odr-venv/lib/python3.10/site-packages/langgraph/pregel/_retry.py", line 744, in arun_with_retry
    return await task.proc.ainvoke(task.input, config)
  File "/tmp/odr-venv/lib/python3.10/site-packages/langgraph/_internal/_runnable.py", line 760, in ainvoke
    input = await step.ainvoke(input, config, **kwargs)
  File "/tmp/odr-venv/lib/python3.10/site-packages/langgraph/_internal/_runnable.py", line 522, in ainvoke
    ret = await self.afunc(*args, **kwargs)
  File "/tmp/odr-venv/lib/python3.10/site-packages/open_deep_research/deep_researcher.py", line 60, in clarify_with_user
    response = await model.ainvoke([HumanMessage(content=clarify_with_user_instructions.format(messages=get_buffer_string(messages), date=get_today_str()))])
  File "/tmp/odr-venv/lib/python3.10/site-packages/langchain_core/runnables/base.py", line 6015, in ainvoke
    return await self.bound.ainvoke(
  File "/tmp/odr-venv/lib/python3.10/site-packages/langchain_core/runnables/retry.py", line 225, in ainvoke
    return await self._acall_with_config(self._ainvoke, input, config, **kwargs)
  File "/tmp/odr-venv/lib/python3.10/site-packages/langchain_core/runnables/base.py", line 2340, in _acall_with_config
    output: Output = await coro_with_context(coro, context)
  File "/tmp/odr-venv/lib/python3.10/site-packages/langchain_core/runnables/retry.py", line 210, in _ainvoke
    async for attempt in self._async_retrying(reraise=True):
  File "/tmp/odr-venv/lib/python3.10/site-packages/tenacity/asyncio/__init__.py", line 170, in __anext__
    do = await self.iter(retry_state=self._retry_state)
  File "/tmp/odr-venv/lib/python3.10/site-packages/tenacity/asyncio/__init__.py", line 157, in iter
    result = await action(retry_state)
  File "/tmp/odr-venv/lib/python3.10/site-packages/tenacity/_utils.py", line 111, in inner
    return call(*args, **kwargs)
  File "/tmp/odr-venv/lib/python3.10/site-packages/tenacity/__init__.py", line 413, in exc_check
    raise retry_exc.reraise()
  File "/tmp/odr-venv/lib/python3.10/site-packages/tenacity/__init__.py", line 184, in reraise
    raise self.last_attempt.result()
  File "/usr/lib/python3.10/concurrent/futures/_base.py", line 451, in result
    return self.__get_result()
  File "/usr/lib/python3.10/concurrent/futures/_base.py", line 403, in __get_result
    raise self._exception
  File "/tmp/odr-venv/lib/python3.10/site-packages/langchain_core/runnables/retry.py", line 212, in _ainvoke
    result = await super().ainvoke(
  File "/tmp/odr-venv/lib/python3.10/site-packages/langchain_core/runnables/base.py", line 6015, in ainvoke
    return await self.bound.ainvoke(
  File "/tmp/odr-venv/lib/python3.10/site-packages/langchain/chat_models/base.py", line 787, in ainvoke
    return await self._model(config).ainvoke(input, config=config, **kwargs)
  File "/tmp/odr-venv/lib/python3.10/site-packages/langchain_core/runnables/base.py", line 3484, in ainvoke
    input_ = await coro_with_context(part(), context, create_task=True)
  File "/tmp/odr-venv/lib/python3.10/site-packages/langchain_core/runnables/base.py", line 6015, in ainvoke
    return await self.bound.ainvoke(
  File "/tmp/odr-venv/lib/python3.10/site-packages/langchain_core/language_models/chat_models.py", line 499, in ainvoke
    llm_result = await self.agenerate_prompt(
  File "/tmp/odr-venv/lib/python3.10/site-packages/langchain_core/language_models/chat_models.py", line 1876, in agenerate_prompt
    return await self.agenerate(
  File "/tmp/odr-venv/lib/python3.10/site-packages/langchain_core/language_models/chat_models.py", line 1834, in agenerate
    raise exceptions[0]
  File "/tmp/odr-venv/lib/python3.10/site-packages/langchain_core/language_models/chat_models.py", line 2167, in _agenerate_with_cache
    result = await self._agenerate(
  File "/tmp/odr-venv/lib/python3.10/site-packages/langchain_openai/chat_models/base.py", line 2023, in _agenerate
    _handle_openai_api_error(e)
  File "/tmp/odr-venv/lib/python3.10/site-packages/langchain_openai/chat_models/base.py", line 2016, in _agenerate
    raw_response = await self.async_client.with_raw_response.create(
  File "/tmp/odr-venv/lib/python3.10/site-packages/openai/_legacy_response.py", line 386, in wrapped
    return cast(LegacyAPIResponse[R], await func(*args, **kwargs))
  File "/home/tjk/myProjects/internship-projects/03-deep-research-agent/scripts/run_odr_isolated.py", line 81, in _async_create_with_thinking_off
    return await _orig_async_create(self, **_with_thinking_off(kwargs))
  File "/tmp/odr-venv/lib/python3.10/site-packages/openai/resources/chat/completions/completions.py", line 2907, in create
    return await self._post(
  File "/tmp/odr-venv/lib/python3.10/site-packages/openai/_base_client.py", line 1996, in post
    return await self.request(cast_to, opts, stream=stream, stream_cls=stream_cls)
  File "/tmp/odr-venv/lib/python3.10/site-packages/openai/_base_client.py", line 1748, in request
    raise APIConnectionError(request=request) from err
openai.APIConnectionError: Connection error. |
| gptr | skipped | - | missing successful report |
