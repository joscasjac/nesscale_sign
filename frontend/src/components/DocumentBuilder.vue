<script setup>
import { ref, computed, nextTick, defineAsyncComponent, watch } from "vue";
import { resolveVariables } from "../variables";
import { editorIcons as Lucide } from "../editor-icons";
import { fieldTypes, repeatField } from "../fields";
import EditorButton from "./EditorButton.vue";
import RichBlock from "./RichBlock.vue";
import VariableInput from "./VariableInput.vue";
const PdfPage = defineAsyncComponent(() => import("./PdfPage.vue"));
const props = defineProps({
	modelValue: Object,
	activePanel: String,
	backgroundUrl: String,
	fields: { type: Array, default: () => [] },
	recipients: { type: Array, default: () => [] },
	variables: { type: Array, default: () => [] },
});
const emit = defineEmits([
	"update:modelValue",
	"update:fields",
	"preview",
	"page-count",
	"update:activePanel",
]);
const root = ref(null),
	current = ref(0),
	importedCount = ref(1),
	selectedId = ref(null),
	selectedFieldId = ref(null),
	error = ref(""),
	history = ref([]),
	future = ref([]),
	textEditor = ref(null),
	variableSearch = ref(""),
	filledPreview = ref(false),
	newVariable = ref(false),
	variableName = ref(""),
	variableValue = ref("");
const pageCount = computed(() =>
	props.backgroundUrl ? importedCount.value : props.modelValue.pages.length,
);
const selected = computed(() =>
	props.modelValue.pages.flatMap((p) => p.blocks).find((b) => b.id === selectedId.value),
);
const selectedField = computed(() =>
	props.fields.find((f) => f.field_key === selectedFieldId.value),
);
const types = ["Text", "Image", "Table", "Divider", "Page break"];
const icons = {
	Text: "Type",
	Heading: "Heading",
	Image: "Image",
	Table: "Table2",
	Divider: "Minus",
	"Page break": "FilePlus",
	Signature: "PenLine",
	Initial: "PenTool",
	Name: "UserRound",
	Email: "Mail",
	"Date Signed": "CalendarCheck",
	Date: "CalendarDays",
	Checkbox: "SquareCheck",
	Dropdown: "ListFilter",
	Label: "Tag",
	Stamp: "Stamp",
};
function snapshot() {
	return JSON.stringify({ data: props.modelValue, fields: props.fields });
}
function remember() {
	history.value.push(snapshot());
	if (history.value.length > 40) history.value.shift();
	future.value = [];
}
function change(fn, record = true) {
	if (record) remember();
	const d = structuredClone(JSON.parse(JSON.stringify(props.modelValue)));
	d.layout = "flow";
	fn(d);
	emit("update:modelValue", d);
}
function restore(frame) {
	const s = JSON.parse(frame);
	emit("update:modelValue", s.data);
	emit("update:fields", s.fields);
	selectedId.value = null;
	selectedFieldId.value = null;
}
function undo() {
	if (history.value.length) {
		future.value.push(snapshot());
		restore(history.value.pop());
	}
}
function redo() {
	if (future.value.length) {
		history.value.push(snapshot());
		restore(future.value.pop());
	}
}
function select(b) {
	if (selectedId.value !== b.id) textEditor.value = null;
	selectedId.value = b.type === "Field" ? null : b.id;
	selectedFieldId.value = b.type === "Field" ? b.field_key : null;
}
function update(key, value) {
	change((d) => {
		const b = d.pages.flatMap((p) => p.blocks).find((b) => b.id === selectedId.value);
		if (b) b[key] = value;
	});
}
function edit(b, values) {
	change(
		(d) =>
			Object.assign(
				d.pages.flatMap((p) => p.blocks).find((x) => x.id === b.id),
				values,
			),
		false,
	);
}
function add(type, p = current.value, index = null) {
	if (type === "Page break") {
		addPage();
		return;
	}
	if (type.startsWith("field:")) {
		addSigningField(type.slice(6), p, index);
		return;
	}
	const id = crypto.randomUUID();
	change((d) => {
		const list = d.pages[p].blocks;
		list.splice(index ?? list.length, 0, {
			id,
			type,
			text:
				type === "Table"
					? "Column 1\tColumn 2\nValue\tValue"
					: "Heading\nAdd text to your document.",
			html:
				type === "Text" ? "<h2>Heading</h2><p>Add text to your document.</p>" : undefined,
			font_size: 16,
			color: "#242a27",
			background: "#ffffff",
			padding: 10,
			margin: 0,
			image_height: 180,
			image_width: 450,
			align: "left",
			line_height: 1.5,
		});
	});
	selectedId.value = id;
	selectedFieldId.value = null;
}
function removeBlock(id) {
	const b = props.modelValue.pages.flatMap((p) => p.blocks).find((b) => b.id === id);
	change((d) => d.pages.forEach((p) => (p.blocks = p.blocks.filter((b) => b.id !== id))));
	if (b?.field_key)
		emit(
			"update:fields",
			props.fields.filter((f) => f.field_key !== b.field_key),
		);
	selectedId.value = null;
	selectedFieldId.value = null;
}
function duplicate() {
	if (!selected.value) return;
	const b = selected.value;
	change((d) => {
		const p = d.pages.find((p) => p.blocks.some((x) => x.id === b.id));
		const i = p.blocks.findIndex((x) => x.id === b.id);
		p.blocks.splice(i + 1, 0, { ...b, id: crypto.randomUUID() });
	});
}
function addPage() {
	if (pageCount.value >= 20) return;
	change((d) => d.pages.push({ blocks: [] }));
	current.value = pageCount.value;
}
function movePage(delta) {
	const from = current.value,
		to = from + delta;
	if (to < 0 || to >= pageCount.value) return;
	change((d) => {
		[d.pages[from], d.pages[to]] = [d.pages[to], d.pages[from]];
	});
	emit(
		"update:fields",
		props.fields.map((f) => ({
			...f,
			page: f.page === from + 1 ? to + 1 : f.page === to + 1 ? from + 1 : f.page,
		})),
	);
	current.value = to;
}
function deletePage() {
	if (pageCount.value === 1) return;
	const i = current.value;
	change((d) => d.pages.splice(i, 1));
	emit(
		"update:fields",
		props.fields
			.filter((f) => f.page !== i + 1)
			.map((f) => ({ ...f, page: f.page > i + 1 ? f.page - 1 : f.page })),
	);
	current.value = 0;
}
function loaded(count) {
	importedCount.value = count;
	emit("page-count", count);
	if (props.backgroundUrl && props.modelValue.pages.length !== count)
		change((d) => {
			d.sourcePdf = d.sourcePdf || props.backgroundUrl;
			d.pages = Array.from({ length: count }, (_, i) => d.pages[i] || { blocks: [] });
		}, false);
}
function goPage(i) {
	current.value = i;
	root.value
		.querySelector('[data-page="' + i + '"]')
		?.scrollIntoView({ behavior: "smooth", block: "start" });
}
function reorder(id, p, index) {
	change((d) => {
		let block;
		for (const page of d.pages) {
			const i = page.blocks.findIndex((b) => b.id === id);
			if (i >= 0) {
				[block] = page.blocks.splice(i, 1);
				if (page === d.pages[p] && i < index) index--;
				break;
			}
		}
		if (block) d.pages[p].blocks.splice(index, 0, block);
	});
}
function drop(e, p, index) {
	e.stopPropagation();
	current.value = p;
	const id = e.dataTransfer.getData("application/x-block");
	if (id) {
		reorder(id, p, index);
		return;
	}
	const type = e.dataTransfer.getData("text/plain");
	if (props.backgroundUrl && type.startsWith("field:")) {
		const rect = e.currentTarget.closest(".flow-page").getBoundingClientRect();
		addSigningField(type.slice(6), p, index, {
			x: (e.clientX - rect.left) / rect.width,
			y: (e.clientY - rect.top) / rect.height,
		});
		return;
	}
	if (types.includes(type) || type.startsWith("field:")) add(type, p, index);
}
function moveBlock(b, p, i, delta) {
	reorder(b.id, p, i + (delta > 0 ? 2 : -1));
}
function fieldFor(b) {
	return props.fields.find((f) => f.field_key === b.field_key);
}
function addSigningField(type, p = current.value, index = null, position = null) {
	if (!fieldTypes.includes(type)) return;
	remember();
	const f = {
		field_key: crypto.randomUUID(),
		field_type: type,
		label: type,
		page: p + 1,
		pos_x: position ? Math.max(0, Math.min(0.55, position.x)) : 0.08,
		pos_y: position ? Math.max(0, Math.min(0.9, position.y)) : 0.2,
		width: type === "Checkbox" ? 0.04 : 0.45,
		height: type === "Signature" ? 0.075 : 0.045,
		required: 1,
		font_size: 12,
		signer_role: props.recipients[0]?.role_key || "",
	};
	emit("update:fields", [...props.fields, f]);
	if (!props.backgroundUrl)
		change((d) => {
			const list = d.pages[p].blocks;
			list.splice(index ?? list.length, 0, {
				id: crypto.randomUUID(),
				type: "Field",
				field_key: f.field_key,
				padding: 10,
				margin: 0,
			});
		}, false);
	selectedFieldId.value = f.field_key;
	selectedId.value = null;
}
function setSigningField(values) {
	remember();
	emit(
		"update:fields",
		props.fields.map((f) => (f.field_key === selectedFieldId.value ? { ...f, ...values } : f)),
	);
}
function repeatSigningField() {
	const f = selectedField.value,
		all = props.fields.map((f) => ({ ...f }));
	try {
		remember();
		const copies = repeatField(f, pageCount.value, all);
		emit("update:fields", [...all, ...copies]);
		if (!props.backgroundUrl)
			change(
				(d) =>
					copies.forEach((c) =>
						d.pages[c.page - 1].blocks.push({
							id: crypto.randomUUID(),
							type: "Field",
							field_key: c.field_key,
							padding: 10,
							margin: 0,
						}),
					),
				false,
			);
	} catch (e) {
		error.value = e.message;
	}
}
function duplicateField() {
	const source = selectedField.value;
	if (!source) return;
	remember();
	const copy = {
		...source,
		field_key: crypto.randomUUID(),
		pos_y: Math.min(1 - source.height, source.pos_y + 0.03),
	};
	emit("update:fields", [...props.fields, copy]);
	if (!props.backgroundUrl)
		change((d) => {
			const blocks = d.pages[source.page - 1].blocks;
			const index = blocks.findIndex((b) => b.field_key === source.field_key);
			blocks.splice(index + 1, 0, {
				...(blocks[index] || { type: "Field", padding: 10, margin: 0 }),
				id: crypto.randomUUID(),
				field_key: copy.field_key,
			});
		}, false);
	selectedFieldId.value = copy.field_key;
}
function removeField() {
	const id = selectedFieldId.value;
	remember();
	emit(
		"update:fields",
		props.fields.filter((f) => f.field_key !== id),
	);
	change(
		(d) => d.pages.forEach((p) => (p.blocks = p.blocks.filter((b) => b.field_key !== id))),
		false,
	);
	selectedFieldId.value = null;
}
let dragging = null;
function startField(e, f) {
	current.value = f.page - 1;
	if (e.button !== 0) return;
	selectedFieldId.value = f.field_key;
	selectedId.value = null;
	const rect = e.currentTarget.parentElement.getBoundingClientRect();
	dragging = { element: e.currentTarget, f, x: e.clientX, y: e.clientY, rect };
	e.currentTarget.setPointerCapture(e.pointerId);
}
function moveField(e) {
	if (!dragging) return;
	const m = dragging;
	m.element.style.transform = `translate3d(${e.clientX - m.x}px,${e.clientY - m.y}px,0)`;
}
function endField(e) {
	if (!dragging) return;
	const m = dragging;
	m.element.style.transform = "";
	dragging = null;
	setSigningField({
		pos_x: Math.max(0, Math.min(1 - m.f.width, m.f.pos_x + (e.clientX - m.x) / m.rect.width)),
		pos_y: Math.max(
			0,
			Math.min(1 - m.f.height, m.f.pos_y + (e.clientY - m.y) / m.rect.height),
		),
	});
}
async function imageFile(e) {
	const f = e.target.files?.[0];
	if (!f) return;
	if (!["image/png", "image/jpeg"].includes(f.type) || f.size > 2 * 1024 * 1024) {
		error.value = "Choose a PNG or JPG smaller than 2 MB.";
		return;
	}
	const reader = new FileReader();
	reader.onload = () => update("image", reader.result);
	reader.readAsDataURL(f);
}
const activeCell = ref({ row: 0, column: 0 });
function rowsFor(b) {
	return b.cells || b.text.split("\n").map((l) => l.split("\t"));
}
async function tableKey(e, b, r, c) {
	if (e.defaultPrevented || e.key !== "Enter" || e.shiftKey) return;
	e.preventDefault();
	const rows = rowsFor(b);
	if (r === rows.length - 1) {
		if (rows.length >= 100) {
			error.value = "Tables support up to 100 rows.";
			return;
		}
		activeCell.value = { row: r, column: c };
		tableChange(b, "row");
		await nextTick();
	}
	const node = root.value.querySelector('[data-block="' + b.id + '"]');
	node.querySelectorAll("tr")[r + 1]?.querySelectorAll(".rich-block")[c]?.focus();
}
function tableCell(b, r, c, e) {
	const rows = rowsFor(b).map((r) => [...r]);
	rows[r][c] = e.text.replace(/\t/g, " ");
	edit(b, { cells: rows, text: rows.map((r) => r.join("\t")).join("\n") });
}
function tableChange(b, action) {
	const rows = rowsFor(b).map((r) => [...r]);
	if (action === "row" && rows.length < 100)
		rows.splice(
			Math.min(activeCell.value.row + 1, rows.length),
			0,
			rows[0].map(() => ""),
		);
	if (action === "column" && rows[0].length < 8)
		rows.forEach((r) => r.splice(Math.min(activeCell.value.column + 1, r.length), 0, ""));
	if (action === "remove-row" && rows.length > 1)
		rows.splice(Math.min(activeCell.value.row, rows.length - 1), 1);
	if (action === "remove-column" && rows[0].length > 1)
		rows.forEach((r) => r.splice(Math.min(activeCell.value.column, r.length - 1), 1));
	edit(b, { cells: rows, text: rows.map((r) => r.join("\t")).join("\n") });
}
function copyVariable(key) {
	navigator.clipboard.writeText("{{" + key + "}}").catch(() => {
		error.value = "Could not copy. Select the variable name to copy it manually.";
	});
}
function createVariable() {
	const name = variableName.value.trim();
	if (!/^[A-Za-z][A-Za-z0-9_]*$/.test(name)) {
		error.value = "Use a name starting with a letter, with letters, numbers or underscores.";
		return;
	}
	const key = "custom." + name;
	if (props.variables.some((v) => v.key === key)) {
		error.value = "That variable already exists.";
		return;
	}
	change((d) => {
		d.variables = [...(d.variables || []), { key, value: variableValue.value }];
	});
	newVariable.value = false;
	variableName.value = "";
	variableValue.value = "";
	error.value = "";
}
function updateVariable(key, value) {
	change((d) => (d.variables = d.variables.map((v) => (v.key === key ? { ...v, value } : v))));
}
function style(b) {
	return {
		background: b.background || "#fff",
		color: b.color || "#242a27",
		fontSize: (b.font_size || 16) + "px",
		fontFamily: b.font_family || "Arial",
		fontWeight: b.type === "Heading" ? 700 : 400,
		textAlign: b.align || "left",
		lineHeight: b.line_height || 1.5,
		padding: (b.padding ?? 10) + "px",
		margin: (b.margin || 0) + "px 0",
	};
}
async function prepare() {
	await nextTick();
	const data = JSON.parse(JSON.stringify(props.modelValue));
	data.resolvedVariables = props.variables;
	data.imported = !!props.backgroundUrl;

	const fields = props.fields.map((f) => ({ ...f }));
	for (const [p, page] of data.pages.entries()) {
		const sheet = root.value.querySelector('[data-page="' + p + '"]');
		const measured = sheet.cloneNode(true);
		measured.style.position = "absolute";
		measured.style.left = "-10000px";
		measured.style.top = "0";
		measured.style.visibility = "hidden";
		root.value.appendChild(measured);
		try {
			for (const content of measured.querySelectorAll(".rich-block")) {
				const walker = document.createTreeWalker(content, NodeFilter.SHOW_TEXT),
					segments = [];
				let text = "";
				while (walker.nextNode()) {
					const node = walker.currentNode;
					segments.push({
						node,
						start: text.length,
						end: text.length + node.textContent.length,
					});
					text += node.textContent;
				}
				for (const match of [
					...text.matchAll(/{{\s*([A-Za-z][A-Za-z0-9_.]*)\s*}}/g),
				].reverse()) {
					const first = segments.find(
							(s) => s.start <= match.index && s.end > match.index,
						),
						last = segments.find(
							(s) =>
								s.start < match.index + match[0].length &&
								s.end >= match.index + match[0].length,
						);
					if (!first || !last) continue;
					const range = document.createRange();
					range.setStart(first.node, match.index - first.start);
					range.setEnd(last.node, match.index + match[0].length - last.start);
					range.deleteContents();
					range.insertNode(
						document.createTextNode(resolveVariables(match[0], props.variables)),
					);
				}
			}
			const rect = measured.getBoundingClientRect();
			for (const b of page.blocks) {
				const node = measured.querySelector('[data-block="' + b.id + '"]');
				if (!node) continue;
				const r = node.getBoundingClientRect();
				const sx = 1,
					sy = 1;
				b.x = Math.round((r.left - rect.left) * sx);
				b.y = Math.round((r.top - rect.top) * sy);
				b.width = Math.round(r.width * sx);
				b.height = Math.ceil(r.height * sy);
				if (b.y + b.height > (props.backgroundUrl ? rect.height - 32 : 810))
					throw Error(
						"Page " + (p + 1) + " is full. Move a block to a new page before saving.",
					);
				if (b.type === "Field") {
					const f = fields.find((f) => f.field_key === b.field_key);
					if (f) {
						const target = node.querySelector(".flow-field").getBoundingClientRect();
						Object.assign(f, {
							page: p + 1,
							pos_x: (target.left - rect.left) / 595,
							pos_y: (target.top - rect.top) / 842,
							width: target.width / 595,
							height: target.height / 842,
						});
					}
				}
			}
		} finally {
			measured.remove();
		}
	}
	data.layout = "flow";
	emit("update:modelValue", data);
	emit("update:fields", fields);
	await nextTick();
}
// Old drafts retain their content and fields when opened in the structured editor.
watch(
	() => [props.modelValue, props.backgroundUrl],
	() => {
		if (props.backgroundUrl || props.modelValue.layout === "flow") return;
		change((d) => {
			d.pages.forEach((p, i) => {
				const keys = new Set(p.blocks.map((b) => b.field_key));
				for (const f of props.fields.filter(
					(f) => f.page === i + 1 && !keys.has(f.field_key),
				))
					p.blocks.push({
						id: crypto.randomUUID(),
						type: "Field",
						field_key: f.field_key,
						y: f.pos_y * 842,
						padding: 10,
					});
				p.blocks.sort((a, b) => (a.y || 0) - (b.y || 0));
				for (const b of p.blocks) {
					if (b.type === "Video link") b.type = "Text";
				}
			});
		}, false);
	},
	{ immediate: true },
);
defineExpose({ prepare });
</script>
<template>
	<div ref="root" class="flow-editor">
		<div class="flow-toolbar">
			<div class="editor-navigation">
				<EditorButton
					v-for="[name, icon] in [
						['Document', 'Plus'],
						['Pages', 'File'],
						['Variables', 'Variable'],
						['Recipients', 'UserRound'],
						['Settings', 'Settings'],
					]"
					:key="name"
					:label="
						name === 'Document'
							? 'Add an element'
							: name === 'Variables'
								? 'Document variables'
								: name
					"
					:icon="icon"
					:active="activePanel === name"
					@click="emit('update:activePanel', name)"
				/>
			</div>
			<div class="text-controls" aria-label="Text formatting">
				<select
					aria-label="Font family"
					:disabled="
						filledPreview || !selected || !['Text', 'Heading'].includes(selected.type)
					"
					:value="selected?.font_family || 'Arial'"
					@change="update('font_family', $event.target.value)"
				>
					<option>Arial</option>
					<option>Times New Roman</option>
					<option>Courier New</option>
				</select>
				<select
					aria-label="Font size"
					:disabled="filledPreview || !selected"
					:value="selected?.font_size || 16"
					@change="update('font_size', Number($event.target.value))"
				>
					<option v-for="n in [10, 12, 14, 16, 18, 24, 28, 32, 40, 48]" :value="n">
						{{ n }} px
					</option>
				</select>
				<select
					aria-label="Text style"
					:disabled="
						filledPreview || !selected || !['Text', 'Heading'].includes(selected.type)
					"
					:value="'p'"
					@change="textEditor?.command('formatBlock', $event.target.value)"
				>
					<option value="p">Paragraph</option>
					<option v-for="n in 5" :value="'h' + n">Heading {{ n }}</option>
				</select>
				<EditorButton
					v-for="[label, icon, cmd] in [
						['Bold', 'Bold', 'bold'],
						['Italic', 'Italic', 'italic'],
						['Underline', 'Underline', 'underline'],
						['Strikethrough', 'Strikethrough', 'strikeThrough'],
						['Bulleted list', 'List', 'insertUnorderedList'],
						['Numbered list', 'ListOrdered', 'insertOrderedList'],
					]"
					:label="label"
					:icon="icon"
					:disabled="
						filledPreview ||
						!selected ||
						!textEditor ||
						!['Text', 'Heading'].includes(selected.type)
					"
					@mousedown.prevent
					@click="textEditor.command(cmd)"
				/>
				<EditorButton
					v-for="[align, icon] in [
						['left', 'AlignLeft'],
						['center', 'AlignCenter'],
						['right', 'AlignRight'],
					]"
					:label="'Align ' + align"
					:icon="icon"
					:disabled="filledPreview || !selected"
					:active="selected?.align === align"
					@mousedown.prevent
					@click="update('align', align)"
				/>
				<select
					aria-label="Line spacing"
					:disabled="filledPreview || !selected"
					:value="selected?.line_height || 1.5"
					@change="update('line_height', Number($event.target.value))"
				>
					<option v-for="n in [1, 1.35, 1.5, 2]" :value="n">{{ n }}</option>
				</select>
				<label class="toolbar-color" data-tooltip="Text color"
					><span class="sr-only">Text color</span
					><input
						type="color"
						:disabled="filledPreview || !selected"
						:value="selected?.color || '#242a27'"
						@input="update('color', $event.target.value)"
				/></label>
				<EditorButton
					label="Insert variable"
					icon="Tag"
					:disabled="filledPreview || !selected || !textEditor"
					@mousedown.prevent
					@click="textEditor.insertMenu()"
				/>
			</div>
			<div class="editor-history">
				<EditorButton
					label="Preview filled variables"
					icon="Eye"
					:active="filledPreview"
					@click="filledPreview = !filledPreview"
				/><EditorButton
					label="Undo"
					icon="Undo2"
					:disabled="!history.length"
					@click="undo"
				/><EditorButton
					label="Redo"
					icon="Redo2"
					:disabled="!future.length"
					@click="redo"
				/>
			</div>
		</div>
		<div class="flow-workspace">
			<aside class="flow-library">
				<template v-if="activePanel === 'Document'"
					><h2>Add an element</h2>
					<h3>Blocks</h3>
					<div class="element-cards">
						<button
							v-for="type in types"
							draggable="true"
							@dragstart="$event.dataTransfer.setData('text/plain', type)"
							@click="add(type)"
						>
							<span class="card-grip">⠿</span
							><component
								:is="Lucide[icons[type]]"
								:size="30"
								aria-hidden="true"
							/><span>{{ type }}</span>
						</button>
					</div>
					<h3>Fillable fields</h3>
					<div class="element-cards field-cards">
						<button
							v-for="type in fieldTypes"
							draggable="true"
							@dragstart="$event.dataTransfer.setData('text/plain', 'field:' + type)"
							@click="addSigningField(type)"
						>
							<span class="card-grip">⠿</span
							><component
								:is="Lucide[icons[type] || 'Type']"
								:size="30"
								aria-hidden="true"
							/><span>{{ type }}</span>
						</button>
					</div></template
				>
				<template v-else-if="activePanel === 'Pages'"
					><h2>Pages</h2>
					<EditorButton
						label="Add page"
						icon="Plus"
						:disabled="!!backgroundUrl || pageCount >= 20"
						@click="addPage" /><button
						v-for="i in pageCount"
						:class="['page-thumbnail', { active: current === i - 1 }]"
						@click="goPage(i - 1)"
					>
						{{ i }}<span class="mini-page-lines"></span>
					</button>
					<div class="button-group">
						<EditorButton
							label="Move page up"
							icon="ArrowUp"
							:disabled="!!backgroundUrl || current === 0"
							@click="movePage(-1)"
						/><EditorButton
							label="Move page down"
							icon="ArrowDown"
							:disabled="!!backgroundUrl || current === pageCount - 1"
							@click="movePage(1)"
						/><EditorButton
							label="Delete page"
							icon="Trash2"
							:disabled="!!backgroundUrl || pageCount === 1"
							@click="deletePage"
						/></div
				></template>
				<template v-else-if="activePanel === 'Variables'"
					><h2>Document variables</h2>
					<div class="variable-search">
						<input
							v-model="variableSearch"
							aria-label="Search variables"
							placeholder="Search"
						/><EditorButton
							label="Add variable"
							icon="Plus"
							@click="newVariable = !newVariable"
						/>
					</div>
					<form v-if="newVariable" class="new-variable" @submit.prevent="createVariable">
						<label
							>Name<input
								v-model="variableName"
								placeholder="project_name"
								required /></label
						><label>Value<input v-model="variableValue" required /></label
						><button class="primary">Add variable</button>
					</form>
					<div
						v-for="v in variables.filter((v) =>
							v.key.toLowerCase().includes(variableSearch.toLowerCase()),
						)"
						class="document-variable"
					>
						<label
							>{{ v.key
							}}<input
								:value="v.value"
								:readonly="!v.key.startsWith('custom.')"
								@change="updateVariable(v.key, $event.target.value)" /></label
						><EditorButton
							:label="'Copy ' + v.key"
							icon="Copy"
							@click="copyVariable(v.key)"
						/></div
				></template>
				<slot v-else name="panel" />
			</aside>
			<div class="flow-canvas">
				<p v-if="error" class="error" role="alert">{{ error }}</p>
				<template v-for="(p, pi) in modelValue.pages" :key="pi"
					><div class="flow-page-heading">
						<span>Page {{ pi + 1 }} of {{ pageCount }}</span
						><EditorButton
							v-if="!backgroundUrl"
							label="Add page"
							icon="Plus"
							@click="addPage"
						/>
					</div>
					<div
						:data-page="pi"
						:class="['flow-page', { 'fixed-pdf': backgroundUrl }]"
						@dragover.prevent
						@drop.prevent="
							backgroundUrl
								? drop($event, pi, p.blocks.length)
								: drop($event, pi, p.blocks.length)
						"
					>
						<template v-if="backgroundUrl"
							><PdfPage
								lazy
								:url="backgroundUrl"
								:page="pi + 1"
								@loaded="loaded"
							/><button
								v-for="f in fields.filter((f) => f.page === pi + 1)"
								class="builder-signing-field"
								:style="{
									left: f.pos_x * 100 + '%',
									top: f.pos_y * 100 + '%',
									width: f.width * 100 + '%',
									height: f.height * 100 + '%',
								}"
								@pointerdown="startField($event, f)"
								@pointermove="moveField"
								@pointerup="endField"
								@pointercancel="dragging = null"
							>
								{{ f.label || f.field_type }}
							</button></template
						>
						<div :class="{ 'pdf-content-overlay': backgroundUrl }">
							<template v-for="(b, i) in p.blocks" :key="b.id"
								><div
									class="block-insertion"
									@dragover.prevent.stop="
										$event.currentTarget.classList.add('over')
									"
									@dragleave="$event.currentTarget.classList.remove('over')"
									@drop.prevent="
										$event.currentTarget.classList.remove('over');
										drop($event, pi, i);
									"
								></div>
								<div
									:data-block="b.id"
									:class="[
										'flow-block',
										{
											selected:
												selectedId === b.id ||
												selectedFieldId === b.field_key,
										},
									]"
									:style="style(b)"
									@click="
										select(b);
										current = pi;
									"
								>
									<div class="flow-block-actions">
										<EditorButton
											label="Move block"
											icon="GripVertical"
											draggable="true"
											@dragstart="
												$event.dataTransfer.setData(
													'application/x-block',
													b.id,
												)
											"
										/><EditorButton
											label="Move block up"
											icon="ArrowUp"
											:disabled="i === 0"
											@click.stop="moveBlock(b, pi, i, -1)"
										/><EditorButton
											label="Move block down"
											icon="ArrowDown"
											:disabled="i === p.blocks.length - 1"
											@click.stop="moveBlock(b, pi, i, 1)"
										/><EditorButton
											label="Delete block"
											icon="Trash2"
											@click.stop="removeBlock(b.id)"
										/>
									</div>
									<template v-if="b.type === 'Field'"
										><button
											v-if="fieldFor(b)"
											class="flow-field"
											:style="{
												width:
													fieldFor(b).field_type === 'Checkbox'
														? '28px'
														: fieldFor(b).width * 595 + 'px',
												height: fieldFor(b).height * 842 + 'px',
											}"
										>
											{{ fieldFor(b).label || fieldFor(b).field_type
											}}<span v-if="fieldFor(b).required"> *</span>
										</button></template
									>
									<template v-else-if="b.type === 'Image'"
										><img
											v-if="b.image"
											:src="b.image"
											alt="Document image"
											:style="{
												width: (b.image_width || 450) + 'px',
												height: (b.image_height || 180) + 'px',
												filter: b.grayscale ? 'grayscale(1)' : 'none',
											}" /><label
											v-else
											class="image-placeholder"
											:style="{ height: (b.image_height || 180) + 'px' }"
											>Select an image<input
												type="file"
												accept="image/png,image/jpeg"
												@click="select(b)"
												@change="imageFile" /></label
									></template>
									<hr v-else-if="b.type === 'Divider'" />
									<template v-else-if="b.type === 'Table'"
										><div v-if="selectedId === b.id" class="table-tools">
											<EditorButton
												v-for="[label, icon, action, badge] in [
													['Insert row below', 'Rows3', 'row', '+'],
													[
														'Insert column right',
														'Columns3',
														'column',
														'+',
													],
													[
														'Delete selected row',
														'Rows3',
														'remove-row',
														'×',
													],
													[
														'Delete selected column',
														'Columns3',
														'remove-column',
														'×',
													],
												]"
												:badge="badge"
												:label="label"
												:icon="icon"
												@click="tableChange(b, action)"
											/>
										</div>
										<table class="editable-table">
											<tbody>
												<tr v-for="(row, r) in rowsFor(b)">
													<td
														v-for="(cell, c) in row"
														@keydown="tableKey($event, b, r, c)"
														@focusin="
															activeCell = { row: r, column: c }
														"
														:aria-label="
															'Row ' + (r + 1) + ' column ' + (c + 1)
														"
													>
														<RichBlock
															:text="cell"
															:variables="variables"
															:preview="filledPreview"
															:label="
																'Row ' +
																(r + 1) +
																' column ' +
																(c + 1)
															"
															@change="tableCell(b, r, c, $event)"
															@focus="
																select(b);
																textEditor = $event;
															"
														/>
													</td>
												</tr>
											</tbody></table
									></template>
									<RichBlock
										v-else
										:html="b.html"
										:text="b.text"
										:variables="variables"
										:preview="filledPreview"
										:label="'Edit ' + b.type"
										@change="edit(b, $event)"
										@focus="
											select(b);
											remember();
											textEditor = $event;
										"
									/></div
							></template>
							<div
								class="block-insertion final-insertion"
								@dragover.prevent.stop="$event.currentTarget.classList.add('over')"
								@dragleave="$event.currentTarget.classList.remove('over')"
								@drop.prevent="
									$event.currentTarget.classList.remove('over');
									drop($event, pi, p.blocks.length);
								"
							>
								<span
									v-if="
										!p.blocks.length &&
										!fields.length &&
										!backgroundUrl &&
										!modelValue.pages.some((page) => page.blocks.length)
									"
									>Drop a block here, or choose one from the left.</span
								>
							</div>
						</div>
					</div></template
				>
			</div>
			<aside class="flow-properties" v-if="selected">
				<div class="dialog-heading">
					<h2>Properties</h2>
					<EditorButton label="Close properties" icon="X" @click="selectedId = null" />
				</div>
				<template v-if="selected.type === 'Image'"
					><label
						>Image<input
							type="file"
							accept="image/png,image/jpeg"
							@change="imageFile" /></label
					><label
						>Alignment<select
							:value="selected.align || 'left'"
							@change="update('align', $event.target.value)"
						>
							<option>left</option>
							<option>center</option>
							<option>right</option>
						</select></label
					><label class="check-label"
						><input
							type="checkbox"
							:checked="selected.grayscale"
							@change="update('grayscale', $event.target.checked)"
						/>Black & white</label
					><label
						>Height<input
							type="number"
							min="20"
							max="700"
							:value="selected.image_height || 180"
							@change="update('image_height', Number($event.target.value))" /></label
					><label
						>Width<input
							type="number"
							min="20"
							max="479"
							:value="selected.image_width || 450"
							@change="update('image_width', Number($event.target.value))" /></label
				></template>
				<label v-if="selected.type !== 'Table'"
					>Background color<input
						type="color"
						:value="selected.background || '#ffffff'"
						@input="update('background', $event.target.value)"
				/></label>
				<div class="spacing-diagram">
					<label v-if="selected.type !== 'Table'"
						>Margin<input
							aria-label="Block margin"
							type="number"
							min="0"
							max="80"
							:value="selected.margin || 0"
							@change="update('margin', Number($event.target.value))"
						/><span>px</span></label
					>
					<div class="padding-box">
						<label
							>Padding<input
								aria-label="Block padding"
								type="number"
								min="0"
								max="80"
								:value="selected.padding ?? 10"
								@change="update('padding', Number($event.target.value))"
							/><span>px</span></label
						><span class="spacing-content"></span>
					</div>
				</div>
				<div class="button-group">
					<EditorButton
						label="Duplicate block"
						icon="Copy"
						@click="duplicate"
					/><EditorButton
						label="Delete block"
						icon="Trash2"
						@click="removeBlock(selected.id)"
					/>
				</div>
			</aside>
			<aside v-if="selectedField" class="flow-properties">
				<div class="dialog-heading">
					<h2>Field properties</h2>
					<button @click="selectedFieldId = null" aria-label="Close field properties">
						×
					</button>
				</div>
				<label
					>Label<input
						:value="selectedField.label"
						@input="setSigningField({ label: $event.target.value })"
				/></label>
				<label
					>Recipient<select
						:value="selectedField.signer_role"
						@change="setSigningField({ signer_role: $event.target.value })"
					>
						<option value="">Choose recipient</option>
						<option v-for="s in recipients" :value="s.role_key">
							{{ s.signer_name || s.role_label || "Recipient" }}
						</option>
					</select></label
				>
				<label class="check-label"
					><input
						type="checkbox"
						:checked="!!selectedField.required"
						@change="setSigningField({ required: $event.target.checked ? 1 : 0 })"
					/>Required</label
				>
				<div class="property-grid">
					<label
						v-for="key in backgroundUrl
							? ['pos_x', 'pos_y', 'width', 'height']
							: ['width', 'height']"
						>{{
							{
								pos_x: "Left (%)",
								pos_y: "Top (%)",
								width: "Width (%)",
								height: "Height (%)",
							}[key]
						}}<input
							type="number"
							min="0"
							max="100"
							:value="Math.round(selectedField[key] * 100)"
							@change="
								setSigningField({ [key]: Number($event.target.value) / 100 })
							"
					/></label>
				</div>
				<label v-if="selectedField.field_type === 'Dropdown'"
					>Options (one per line)<textarea
						:value="selectedField.options"
						@input="setSigningField({ options: $event.target.value })"
					/>
				</label>
				<label
					>Prefilled value<input
						:value="selectedField.default_value"
						@input="setSigningField({ default_value: $event.target.value })"
				/></label>
				<label
					>Font size<input
						type="number"
						min="6"
						max="48"
						:value="selectedField.font_size"
						@change="setSigningField({ font_size: Number($event.target.value) })"
				/></label>
				<label
					>ERP field mapping<input
						:value="selectedField.mapping_key"
						@input="setSigningField({ mapping_key: $event.target.value })"
				/></label>
				<label class="check-label"
					><input
						type="checkbox"
						:checked="!!selectedField.read_only"
						@change="setSigningField({ read_only: $event.target.checked ? 1 : 0 })"
					/>Read only</label
				>
				<button :disabled="pageCount < 2" @click="repeatSigningField">
					Repeat on all pages
				</button>
				<EditorButton
					label="Duplicate field"
					icon="Copy"
					@click="duplicateField"
				/><EditorButton label="Delete field" icon="Trash2" @click="removeField" />
			</aside>
			<aside v-if="!selected && !selectedField" class="flow-properties properties-empty">
				<h2>Properties</h2>
				<p>Select a block or field to adjust its properties.</p>
			</aside>
		</div>
	</div>
</template>
