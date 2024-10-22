<!-- Documents.svelte -->
<script lang="ts">
    import { createEventDispatcher } from 'svelte';
    import { documents, mobile } from '$lib/stores';
    import { removeFirstHashWord, isValidHttpUrl } from '$lib/utils';
    import { tick, getContext } from 'svelte';
    import { toast } from 'svelte-sonner';
	import { DropdownMenu } from 'bits-ui';
    import { flyAndScale } from '$lib/utils/transitions';
	import ChevronDown from '../icons/ChevronDown.svelte';

    const i18n = getContext('i18n');
    const dispatch = createEventDispatcher();

    export let prompt = '';
    export let className = 'w-[32rem]';
    let selectedIdx = 0;
	let filteredItems = [];
	let filteredDocs = [];
	let collections = [];
    let selectedModelIdx = 0;
    let shows = false;
    let selectedDocName = 'Select GPT'; // Default placeholder

    $: collections = [
		...($documents.length > 0
			? [
					{
						name: 'All Documents',
						type: 'collection',
						title: $i18n.t('All Documents'),
						collection_names: $documents.map((doc) => doc.collection_name)
					}
			  ]
			: []),
		...$documents
			.reduce((a, e, i, arr) => {
				return [...new Set([...a, ...(e?.content?.tags ?? []).map((tag) => tag.name)])];
			}, [])
			.map((tag) => ({
				name: tag,
				type: 'collection',
				collection_names: $documents
					.filter((doc) => (doc?.content?.tags ?? []).map((tag) => tag.name).includes(tag))
					.map((doc) => doc.collection_name)
			}))
	];
	//tagsDocument stores documents with tags
    $: tagsDocument = [...$documents
			.reduce((a, e, i, arr) => {
				return [...new Set([...a, ...(e?.content?.tags ?? []).map((tag) => tag.name)])];
			}, [])
			.map((tag) => ({
				name: tag,
				type: 'collection',
				collection_names: $documents
					.filter((doc) => (doc?.content?.tags ?? []).map((tag) => tag.name).includes(tag))
					.map((doc) => doc.collection_name)
			}))]
    

			type ObjectWithName = {
		name: string;
	};

	const findByName = (obj: ObjectWithName, prompt: string) => {
		const name = obj.name.toLowerCase();
		return name.includes(prompt.toLowerCase().split(' ')?.at(0)?.substring(1) ?? '');
	};

	export const selectUp = () => {
		selectedIdx = Math.max(0, selectedIdx - 1);
	};

	export const selectDown = () => {
		selectedIdx = Math.min(selectedIdx + 1, filteredItems.length - 1);
	};


    const confirmSelect = async (doc) => {
        const event = new CustomEvent('selectDoc', { detail: doc });
        dispatchEvent(event);
        const chatInputElement = document.getElementById('chat-textarea');
        await tick();
        chatInputElement?.focus();
        await tick();

        selectedDocName = doc.name; // Update the selected document name
    };

</script>

<DropdownMenu.Root
    bind:open={shows}
    onOpenChange={async () => {
        selectedModelIdx = 0;
    }}
    closeFocus={false}
>
    <DropdownMenu.Trigger
        class="relative w-full font-primary"
        aria-label="Select GPT Model"
        aria-expanded={shows}
        aria-controls="dropdown-content"
    >
        <div class="flex w-full text-left px-2 outline-none bg-transparent truncate text-lg font-semibold placeholder-gray-400 focus:outline-none">
            {selectedDocName} <!-- Display the selected document name here -->
            <ChevronDown className="self-center ml-2 size-3" strokeWidth="2.5" />
        </div>
    </DropdownMenu.Trigger>

    <DropdownMenu.Content
        id="dropdown-content"
        class="z-40 {$mobile ? 'w-full' : `${className}`} max-w-200px justify-start rounded-xl bg-white dark:bg-gray-850 dark:text-white shadow-lg border border-gray-300/30 dark:border-gray-700/40 outline-none"
        transition={flyAndScale}
        side="bottom"  
        align="start"  
        sideOffset={10}
    >
        <div class="px-3 my-2 max-h-64 overflow-y-auto scrollbar-hidden group">
            {#each tagsDocument as doc, docIdx}
                <button
                    class="flex w-full text-left font-medium line-clamp-1 select-none items-center rounded-lg py-2 pl-3 pr-1.5 text-sm text-gray-700 dark:text-gray-100 outline-none transition-all duration-150 hover:bg-gray-100 dark:hover:bg-gray-800 data-[highlighted]:bg-muted {docIdx === selectedIdx ? 'bg-gray-100 dark:bg-gray-800' : ''}"
                    type="button"
                    on:click={() => {
                        console.log(doc);
                        confirmSelect(doc);
                    }}
                    on:mousemove={() => {
                        selectedIdx = docIdx;
                    }}
                >
                    {#if doc.type === 'collection'}
                        <div class="font-medium text-black dark:text-gray-100 line-clamp-1">
                            {doc?.title ?? doc.name}
                        </div>
                    {:else}
                        <div class="font-medium text-black dark:text-gray-100 line-clamp-1">
                            #{doc.name} ({doc.filename})
                        </div>
                        <div class="text-xs text-gray-600 dark:text-gray-100 line-clamp-1">
                            {doc.title}
                        </div>
                    {/if}
                </button>
            {/each}
        </div>
    </DropdownMenu.Content>
</DropdownMenu.Root>