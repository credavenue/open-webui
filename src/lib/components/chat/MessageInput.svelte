<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, tick, getContext, createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();

	import {
		type Model,
		mobile,
		settings,
		showSidebar,
		models,
		config,
		showCallOverlay,
		tools,
		user as _user,
		chatId
	} from '$lib/stores';
	import { blobToFile, findWordIndices } from '$lib/utils';

	import { transcribeAudio } from '$lib/apis/audio';
	import { processDocToVectorDB } from '$lib/apis/rag';
	import { uploadFile } from '$lib/apis/files';

	import {
		SUPPORTED_FILE_TYPE,
		SUPPORTED_FILE_EXTENSIONS,
		WEBUI_BASE_URL,
		WEBUI_API_BASE_URL
	} from '$lib/constants';

	import Tooltip from '../common/Tooltip.svelte';
	import InputMenu from './MessageInput/InputMenu.svelte';
	import Headphone from '../icons/Headphone.svelte';
	import VoiceRecording from './MessageInput/VoiceRecording.svelte';
	import FileItem from '../common/FileItem.svelte';
	import FilesOverlay from './MessageInput/FilesOverlay.svelte';
	import Commands from './MessageInput/Commands.svelte';
	import XMark from '../icons/XMark.svelte';
    import Doc from '../layout/Doc.svelte';
	import { createNewChat, getChatById } from '$lib/apis/chats';
	import { goto } from '$app/navigation';
	const i18n = getContext('i18n');

	export let transparentBackground = false;
	export let initNewChat: Function;

	export let submitPrompt: Function;
	export let stopResponse: Function;

	export let autoScroll = false;

	export let atSelectedModel: Model | undefined;
	export let selectedModels: [''];

	let recording = false;

	let chatTextAreaElement: HTMLTextAreaElement;
	let filesInputElement;

	let commandsElement;

	let inputFiles;
	let dragged = false;
    
	let selectedChatId = null;
	let user = null;
	let chatInputPlaceholder = '';

	export let files = [];

	export let availableToolIds = [];
	export let selectedToolIds = [];
	export let webSearchEnabled = false;

	export let prompt = '';
	export let messages = [];

	let visionCapableModels = [];
	$: visionCapableModels = [...(atSelectedModel ? [atSelectedModel] : selectedModels)].filter(
		(model) => $models.find((m) => m.id === model)?.info?.meta?.capabilities?.vision ?? true
	);

	$: if (prompt) {
		if (chatTextAreaElement) {
			chatTextAreaElement.style.height = '';
			chatTextAreaElement.style.height = Math.min(chatTextAreaElement.scrollHeight, 200) + 'px';
		}
	}

	const scrollToBottom = () => {
		const element = document.getElementById('messages-container');
		element.scrollTo({
			top: element.scrollHeight,
			behavior: 'smooth'
		});
	};

	const uploadFileHandler = async (file) => {
		console.log(file);

		// Check if the file is an audio file and transcribe/convert it to text file
		if (['audio/mpeg', 'audio/wav'].includes(file['type'])) {
			const res = await transcribeAudio(localStorage.token, file).catch((error) => {
				toast.error(error);
				return null;
			});

			if (res) {
				console.log(res);
				const blob = new Blob([res.text], { type: 'text/plain' });
				file = blobToFile(blob, `${file.name}.txt`);
			}
		}

		const fileItem = {
			type: 'file',
			file: '',
			id: null,
			url: '',
			name: file.name,
			collection_name: '',
			status: '',
			size: file.size,
			error: ''
		};
		files = [...files, fileItem];

		try {
			const uploadedFile = await uploadFile(localStorage.token, file);

			if (uploadedFile) {
				fileItem.status = 'uploaded';
				fileItem.file = uploadedFile;
				fileItem.id = uploadedFile.id;
				fileItem.url = `${WEBUI_API_BASE_URL}/files/${uploadedFile.id}`;

				// TODO: Check if tools & functions have files support to skip this step to delegate file processing
				// Default Upload to VectorDB
				if (
					SUPPORTED_FILE_TYPE.includes(file['type']) ||
					SUPPORTED_FILE_EXTENSIONS.includes(file.name.split('.').at(-1))
				) {
					processFileItem(fileItem);
				} else {
					toast.error(
						$i18n.t(`Unknown file type '{{file_type}}'. Proceeding with the file upload anyway.`, {
							file_type: file['type']
						})
					);
					processFileItem(fileItem);
				}
			} else {
				files = files.filter((item) => item.status !== null);
			}
		} catch (e) {
			toast.error(e);
			files = files.filter((item) => item.status !== null);
		}
	};

	const processFileItem = async (fileItem) => {
		try {
			const res = await processDocToVectorDB(localStorage.token, fileItem.id);

			if (res) {
				fileItem.status = 'processed';
				fileItem.collection_name = res.collection_name;
				files = files;
			}
		} catch (e) {
			// Remove the failed doc from the files array
			// files = files.filter((f) => f.id !== fileItem.id);
			toast.error(e);
			fileItem.status = 'processed';
			files = files;
		}
	};

	const inputFilesHandler = async (inputFiles) => {
		inputFiles.forEach((file) => {
			console.log(file, file.name.split('.').at(-1));

			if (
				($config?.file?.max_size ?? null) !== null &&
				file.size > ($config?.file?.max_size ?? 0) * 1024 * 1024
			) {
				toast.error(
					$i18n.t(`File size should not exceed {{maxSize}} MB.`, {
						maxSize: $config?.file?.max_size
					})
				);
				return;
			}

			if (['image/gif', 'image/webp', 'image/jpeg', 'image/png'].includes(file['type'])) {
				if (visionCapableModels.length === 0) {
					toast.error($i18n.t('Selected model(s) do not support image inputs'));
					return;
				}
				let reader = new FileReader();
				reader.onload = (event) => {
					files = [
						...files,
						{
							type: 'image',
							url: `${event.target.result}`
						}
					];
				};
				reader.readAsDataURL(file);
			} else {
				uploadFileHandler(file);
			}
		});
	};
    
	const handleSelectDoc = async (event) => {
		selectedChatId = null;
					await goto('/');
					const newChatButton = document.getElementById('new-chat-button');
					setTimeout(() => {
						newChatButton?.click();
						if ($mobile) {
							showSidebar.set(false);
						}
					}, 0);
        console.log(event);
		files = [];
							const newfiles = 
								{
									type: event?.detail?.type ?? 'file',
									...event.detail,
									status: 'processed'
								}
							;
		files = [newfiles];
   
    };

	onMount(() => {
		window.setTimeout(() => chatTextAreaElement?.focus(), 0);

		const dropZone = document.querySelector('body');

		const handleKeyDown = (event: KeyboardEvent) => {
			if (event.key === 'Escape') {
				console.log('Escape');
				dragged = false;
			}
		};

		const onDragOver = (e) => {
			e.preventDefault();
			dragged = true;
		};

		const onDragLeave = () => {
			dragged = false;
		};

		const onDrop = async (e) => {
			e.preventDefault();
			console.log(e);

			if (e.dataTransfer?.files) {
				const inputFiles = Array.from(e.dataTransfer?.files);
				if (inputFiles && inputFiles.length > 0) {
					console.log(inputFiles);
					inputFilesHandler(inputFiles);
				} else {
					toast.error($i18n.t(`File not found.`));
				}
			}

			dragged = false;
		};

		window.addEventListener('keydown', handleKeyDown);
		window.addEventListener('selectDoc', handleSelectDoc);
		dropZone?.addEventListener('dragover', onDragOver);
		dropZone?.addEventListener('drop', onDrop);
		dropZone?.addEventListener('dragleave', onDragLeave);

		return () => {
			window.removeEventListener('keydown', handleKeyDown);

			dropZone?.removeEventListener('dragover', onDragOver);
			dropZone?.removeEventListener('drop', onDrop);
			dropZone?.removeEventListener('dragleave', onDragLeave);
		};
	});
</script>

<FilesOverlay show={dragged} />

<div class="w-full font-primary">
	<div class=" -mb-0.5 mx-auto inset-x-0 bg-transparent flex justify-center">
		<div class="flex flex-col max-w-6xl px-2.5 md:px-6 w-full">
			<div class="relative">
				{#if autoScroll === false && messages.length > 0}
					<div
						class=" absolute -top-12 left-0 right-0 flex justify-center z-30 pointer-events-none"
					>
						<button
							class=" bg-white border border-gray-100 dark:border-none dark:bg-white/20 p-1.5 rounded-full pointer-events-auto"
							on:click={() => {
								autoScroll = true;
								scrollToBottom();
							}}
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 20 20"
								fill="currentColor"
								class="w-5 h-5"
							>
								<path
									fill-rule="evenodd"
									d="M10 3a.75.75 0 01.75.75v10.638l3.96-4.158a.75.75 0 111.08 1.04l-5.25 5.5a.75.75 0 01-1.08 0l-5.25-5.5a.75.75 0 111.08-1.04l3.96 4.158V3.75A.75.75 0 0110 3z"
									clip-rule="evenodd"
								/>
							</svg>
						</button>
					</div>
				{/if}
			</div>

			<div class="w-full relative">
				{#if atSelectedModel !== undefined}
					<div
						class="px-3 py-2.5 text-left w-full flex justify-between items-center absolute bottom-0.5 left-0 right-0 bg-gradient-to-t from-50% from-white dark:from-gray-900 z-10"
					>
						<div class="flex items-center gap-2 text-sm dark:text-gray-500">
							<img
								crossorigin="anonymous"
								alt="model profile"
								class="size-5 max-w-[28px] object-cover rounded-full"
								src={$models.find((model) => model.id === atSelectedModel.id)?.info?.meta
									?.profile_image_url ??
									($i18n.language === 'dg-DG'
										? `/doge.png`
										: `${WEBUI_BASE_URL}/static/favicon.png`)}
							/>
							<div>
								Talking to <span class=" font-medium">{atSelectedModel.name}</span>
							</div>
						</div>
						<div>
							<button
								class="flex items-center"
								on:click={() => {
									atSelectedModel = undefined;
								}}
							>
								<XMark />
							</button>
						</div>
					</div>
				{/if}

				<Commands
					bind:this={commandsElement}
					bind:prompt
					bind:files
					on:select={(e) => {
						const data = e.detail;

						if (data?.type === 'model') {
							atSelectedModel = data.data;
						}

						chatTextAreaElement?.focus();
					}}
				/>
			</div>
		</div>
	</div>

	<div class="{transparentBackground ? 'bg-transparent' : 'bg-white dark:bg-gray-900'} ">
		<div class="max-w-6xl px-2.5 md:px-6 mx-auto inset-x-0">
			<div class=" pb-2">
				<input
					bind:this={filesInputElement}
					bind:files={inputFiles}
					type="file"
					hidden
					multiple
					on:change={async () => {
						if (inputFiles && inputFiles.length > 0) {
							const _inputFiles = Array.from(inputFiles);
							inputFilesHandler(_inputFiles);
						} else {
							toast.error($i18n.t(`File not found.`));
						}

						filesInputElement.value = '';
					}}
				/>

				{#if recording}
					<VoiceRecording
						bind:recording
						on:cancel={async () => {
							recording = false;

							await tick();
							document.getElementById('chat-textarea')?.focus();
						}}
						on:confirm={async (e) => {
							const response = e.detail;
							prompt = `${prompt}${response} `;

							recording = false;

							await tick();
							document.getElementById('chat-textarea')?.focus();

							if ($settings?.speechAutoSend ?? false) {
								submitPrompt(prompt);
							}
						}}
					/>
				{:else}
					<form
						class="w-full flex gap-1.5"
						on:submit|preventDefault={() => {
							// check if selectedModels support image input
							submitPrompt(prompt);
						}}
					>
						<div
							class="flex-1 flex flex-col relative w-full rounded-3xl px-1.5 bg-gray-50 dark:bg-gray-850 dark:text-gray-100"
							dir={$settings?.chatDirection ?? 'LTR'}
						><!--
							{#if files.length > 0}
								<div class="mx-1 mt-2.5 mb-1 flex flex-wrap gap-2">
									{#each files as file, fileIdx}
										{#if file.type === 'image'}
											<div class=" relative group">
												<div class="relative">
													<img
														src={file.url}
														alt="input"
														class=" h-16 w-16 rounded-xl object-cover"
													/>
													{#if atSelectedModel ? visionCapableModels.length === 0 : selectedModels.length !== visionCapableModels.length}
														<Tooltip
															className=" absolute top-1 left-1"
															content={$i18n.t('{{ models }}', {
																models: [...(atSelectedModel ? [atSelectedModel] : selectedModels)]
																	.filter((id) => !visionCapableModels.includes(id))
																	.join(', ')
															})}
														>
															<svg
																xmlns="http://www.w3.org/2000/svg"
																viewBox="0 0 24 24"
																fill="currentColor"
																class="size-4 fill-yellow-300"
															>
																<path
																	fill-rule="evenodd"
																	d="M9.401 3.003c1.155-2 4.043-2 5.197 0l7.355 12.748c1.154 2-.29 4.5-2.599 4.5H4.645c-2.309 0-3.752-2.5-2.598-4.5L9.4 3.003ZM12 8.25a.75.75 0 0 1 .75.75v3.75a.75.75 0 0 1-1.5 0V9a.75.75 0 0 1 .75-.75Zm0 8.25a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Z"
																	clip-rule="evenodd"
																/>
															</svg>
														</Tooltip>
													{/if}
												</div>
												<div class=" absolute -top-1 -right-1">
													<button
														class=" bg-gray-400 text-white border border-white rounded-full group-hover:visible invisible transition"
														type="button"
														on:click={() => {
															files.splice(fileIdx, 1);
															files = files;
														}}
													>
														<svg
															xmlns="http://www.w3.org/2000/svg"
															viewBox="0 0 20 20"
															fill="currentColor"
															class="w-4 h-4"
														>
															<path
																d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
															/>
														</svg>
													</button>
												</div>
											</div>
										{:else}
											<FileItem
												name={file.name}
												type={file.type}
												size={file?.size}
												status={file.status}
												dismissible={true}
												on:dismiss={() => {
													files.splice(fileIdx, 1);
													files = files;
												}}
											/>
										{/if}
									{/each}
								</div>
							{/if}
					-->
							<div class=" flex">
								<div class=" ml-0.5 self-end mb-1.5 flex space-x-1">
									<InputMenu
										bind:webSearchEnabled
										bind:selectedToolIds
										tools={$tools.reduce((a, e, i, arr) => {
											if (availableToolIds.includes(e.id) || ($_user?.role ?? 'user') === 'admin') {
												a[e.id] = {
													name: e.name,
													description: e.meta.description,
													enabled: false
												};
											}
											return a;
										}, {})}
										uploadFilesHandler={() => {
											filesInputElement.click();
										}}
										onClose={async () => {
											await tick();
											chatTextAreaElement?.focus();
										}}
									>
										<button
											class="bg-gray-50 hover:bg-gray-100 text-gray-800 dark:bg-gray-850 dark:text-white dark:hover:bg-gray-800 transition rounded-full p-2 outline-none focus:outline-none"
											type="button"
											aria-label="More"
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 16 16"
												fill="currentColor"
												class="size-5"
											>
												<path
													d="M8.75 3.75a.75.75 0 0 0-1.5 0v3.5h-3.5a.75.75 0 0 0 0 1.5h3.5v3.5a.75.75 0 0 0 1.5 0v-3.5h3.5a.75.75 0 0 0 0-1.5h-3.5v-3.5Z"
												/>
											</svg>
										</button>
									</InputMenu>
								</div>

								<textarea
									id="chat-textarea"
									bind:this={chatTextAreaElement}
									class="scrollbar-hidden bg-gray-50 dark:bg-gray-850 dark:text-gray-100 outline-none w-full py-3 px-1 rounded-xl resize-none h-[48px]"
									placeholder={chatInputPlaceholder !== ''
										? chatInputPlaceholder
										: $i18n.t('Message YubiGPT')}
									bind:value={prompt}
									on:keypress={(e) => {
										if (
											!$mobile ||
											!(
												'ontouchstart' in window ||
												navigator.maxTouchPoints > 0 ||
												navigator.msMaxTouchPoints > 0
											)
										) {
											// Prevent Enter key from creating a new line
											if (e.key === 'Enter' && !e.shiftKey) {
												e.preventDefault();
											}

											// Submit the prompt when Enter key is pressed
											if (prompt !== '' && e.key === 'Enter' && !e.shiftKey) {
												submitPrompt(prompt);
											}
										}
									}}
									on:keydown={async (e) => {
										const isCtrlPressed = e.ctrlKey || e.metaKey; // metaKey is for Cmd key on Mac
										const commandsContainerElement = document.getElementById('commands-container');

										// Check if Ctrl + R is pressed
										if (prompt === '' && isCtrlPressed && e.key.toLowerCase() === 'r') {
											e.preventDefault();
											console.log('regenerate');

											const regenerateButton = [
												...document.getElementsByClassName('regenerate-response-button')
											]?.at(-1);

											regenerateButton?.click();
										}

										if (prompt === '' && e.key == 'ArrowUp') {
											e.preventDefault();

											const userMessageElement = [
												...document.getElementsByClassName('user-message')
											]?.at(-1);

											const editButton = [
												...document.getElementsByClassName('edit-user-message-button')
											]?.at(-1);

											console.log(userMessageElement);

											userMessageElement.scrollIntoView({ block: 'center' });
											editButton?.click();
										}

										if (commandsContainerElement && e.key === 'ArrowUp') {
											e.preventDefault();
											commandsElement.selectUp();

											const commandOptionButton = [
												...document.getElementsByClassName('selected-command-option-button')
											]?.at(-1);
											commandOptionButton.scrollIntoView({ block: 'center' });
										}

										if (commandsContainerElement && e.key === 'ArrowDown') {
											e.preventDefault();
											commandsElement.selectDown();

											const commandOptionButton = [
												...document.getElementsByClassName('selected-command-option-button')
											]?.at(-1);
											commandOptionButton.scrollIntoView({ block: 'center' });
										}

										if (commandsContainerElement && e.key === 'Enter') {
											e.preventDefault();

											const commandOptionButton = [
												...document.getElementsByClassName('selected-command-option-button')
											]?.at(-1);

											if (e.shiftKey) {
												prompt = `${prompt}\n`;
											} else if (commandOptionButton) {
												commandOptionButton?.click();
											} else {
												document.getElementById('send-message-button')?.click();
											}
										}

										if (commandsContainerElement && e.key === 'Tab') {
											e.preventDefault();

											const commandOptionButton = [
												...document.getElementsByClassName('selected-command-option-button')
											]?.at(-1);

											commandOptionButton?.click();
										} else if (e.key === 'Tab') {
											const words = findWordIndices(prompt);

											if (words.length > 0) {
												const word = words.at(0);
												const fullPrompt = prompt;

												prompt = prompt.substring(0, word?.endIndex + 1);
												await tick();

												e.target.scrollTop = e.target.scrollHeight;
												prompt = fullPrompt;
												await tick();

												e.preventDefault();
												e.target.setSelectionRange(word?.startIndex, word.endIndex + 1);
											}

											e.target.style.height = '';
											e.target.style.height = Math.min(e.target.scrollHeight, 200) + 'px';
										}

										if (e.key === 'Escape') {
											console.log('Escape');
											atSelectedModel = undefined;
										}
									}}
									rows="1"
									on:input={async (e) => {
										e.target.style.height = '';
										e.target.style.height = Math.min(e.target.scrollHeight, 200) + 'px';
										user = null;
									}}
									on:focus={async (e) => {
										e.target.style.height = '';
										e.target.style.height = Math.min(e.target.scrollHeight, 200) + 'px';
									}}
									on:paste={async (e) => {
										const clipboardData = e.clipboardData || window.clipboardData;

										if (clipboardData && clipboardData.items) {
											for (const item of clipboardData.items) {
												if (item.type.indexOf('image') !== -1) {
													const blob = item.getAsFile();
													const reader = new FileReader();

													reader.onload = function (e) {
														files = [
															...files,
															{
																type: 'image',
																url: `${e.target.result}`
															}
														];
													};

													reader.readAsDataURL(blob);
												}
											}
										}
									}}
								/>

								<div class="self-end mb-2 flex space-x-1 mr-1">
									{#if messages.length == 0 || messages.at(-1).done == true}
										<Tooltip content={$i18n.t('Record voice')}>
											<button
												id="voice-input-button"
												class=" text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-850 transition rounded-full p-1.5 mr-0.5 self-center"
												type="button"
												on:click={async () => {
													try {
														let stream = await navigator.mediaDevices
															.getUserMedia({ audio: true })
															.catch(function (err) {
																toast.error(
																	$i18n.t(
																		`Permission denied when accessing microphone: {{error}}`,
																		{
																			error: err
																		}
																	)
																);
																return null;
															});

														if (stream) {
															recording = true;
															const tracks = stream.getTracks();
															tracks.forEach((track) => track.stop());
														}
														stream = null;
													} catch {
														toast.error($i18n.t('Permission denied when accessing microphone'));
													}
												}}
												aria-label="Voice Input"
											>
												<svg
													xmlns="http://www.w3.org/2000/svg"
													viewBox="0 0 20 20"
													fill="currentColor"
													class="w-5 h-5 translate-y-[0.5px]"
												>
													<path d="M7 4a3 3 0 016 0v6a3 3 0 11-6 0V4z" />
													<path
														d="M5.5 9.643a.75.75 0 00-1.5 0V10c0 3.06 2.29 5.585 5.25 5.954V17.5h-1.5a.75.75 0 000 1.5h4.5a.75.75 0 000-1.5h-1.5v-1.546A6.001 6.001 0 0016 10v-.357a.75.75 0 00-1.5 0V10a4.5 4.5 0 01-9 0v-.357z"
													/>
												</svg>
											</button>
										</Tooltip>
									{/if}
								</div>
							</div>
						</div>
						<div class="flex items-end w-10">
							{#if messages.length == 0 || messages.at(-1).done == true}
								{#if prompt === ''}
									<div class=" flex items-center mb-1">
										<Tooltip content={$i18n.t('Call')}>
											<button
												class=" text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-850 transition rounded-full p-2 self-center"
												type="button"
												on:click={async () => {
													if (selectedModels.length > 1) {
														toast.error($i18n.t('Select only one model to call'));

														return;
													}

													if ($config.audio.stt.engine === 'web') {
														toast.error(
															$i18n.t('Call feature is not supported when using Web STT engine')
														);

														return;
													}
													// check if user has access to getUserMedia
													try {
														let stream = await navigator.mediaDevices.getUserMedia({ audio: true });
														// If the user grants the permission, proceed to show the call overlay

														if (stream) {
															const tracks = stream.getTracks();
															tracks.forEach((track) => track.stop());
														}

														stream = null;

														showCallOverlay.set(true);
														dispatch('call');
													} catch (err) {
														// If the user denies the permission or an error occurs, show an error message
														toast.error($i18n.t('Permission denied when accessing media devices'));
													}
												}}
												aria-label="Call"
											>
												<Headphone className="size-6" />
											</button>
										</Tooltip>
									</div>
								{:else}
									<div class=" flex items-center mb-1">
										<Tooltip content={$i18n.t('Send message')}>
											<button
												id="send-message-button"
												class="{prompt !== ''
													? 'bg-black text-white hover:bg-gray-900 dark:bg-white dark:text-black dark:hover:bg-gray-100 '
													: 'text-white bg-gray-200 dark:text-gray-900 dark:bg-gray-700 disabled'} transition rounded-full p-1.5 m-0.5 self-center"
												type="submit"
												disabled={prompt === ''}
											>
												<svg
													xmlns="http://www.w3.org/2000/svg"
													viewBox="0 0 16 16"
													fill="currentColor"
													class="size-6"
												>
													<path
														fill-rule="evenodd"
														d="M8 14a.75.75 0 0 1-.75-.75V4.56L4.03 7.78a.75.75 0 0 1-1.06-1.06l4.5-4.5a.75.75 0 0 1 1.06 0l4.5 4.5a.75.75 0 0 1-1.06 1.06L8.75 4.56v8.69A.75.75 0 0 1 8 14Z"
														clip-rule="evenodd"
													/>
												</svg>
											</button>
										</Tooltip>
									</div>
								{/if}
							{:else}
								<div class=" flex items-center mb-1.5">
									<button
										class="bg-white hover:bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-white dark:hover:bg-gray-800 transition rounded-full p-1.5"
										on:click={() => {
											stopResponse();
										}}
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											viewBox="0 0 24 24"
											fill="currentColor"
											class="size-6"
										>
											<path
												fill-rule="evenodd"
												d="M2.25 12c0-5.385 4.365-9.75 9.75-9.75s9.75 4.365 9.75 9.75-4.365 9.75-9.75 9.75S2.25 17.385 2.25 12zm6-2.438c0-.724.588-1.312 1.313-1.312h4.874c.725 0 1.313.588 1.313 1.313v4.874c0 .725-.588 1.313-1.313 1.313H9.564a1.312 1.312 0 01-1.313-1.313V9.564z"
												clip-rule="evenodd"
											/>
										</svg>
									</button>
								</div>
							{/if}
						</div>
					</form>
				{/if}

				<div class="mt-1.5 text-xs text-gray-500 text-center line-clamp-1">
					{$i18n.t('LLMs can make mistakes. Verify important information.')}
				</div>
			</div>
		</div>
	</div>
</div>

<style>
	.scrollbar-hidden:active::-webkit-scrollbar-thumb,
	.scrollbar-hidden:focus::-webkit-scrollbar-thumb,
	.scrollbar-hidden:hover::-webkit-scrollbar-thumb {
		visibility: visible;
	}
	.scrollbar-hidden::-webkit-scrollbar-thumb {
		visibility: hidden;
	}
</style>
