<script setup>
import { ref, computed, defineAsyncComponent, onBeforeUnmount } from "vue";
import { fieldTypes, repeatField } from "../fields";
const PdfPage = defineAsyncComponent(() => import("./PdfPage.vue"));
const importedCount = ref(1);
const props = defineProps({
	modelValue: Object,
	activePanel: String,
	backgroundUrl: String,
	fields: { type: Array, default: () => [] },
	recipients: { type: Array, default: () => [] },
});
const emit = defineEmits(["update:modelValue", "update:fields", "preview", "page-count"]);
const pageCount = computed(() =>
	props.backgroundUrl ? importedCount.value : props.modelValue.pages.length,
);
const current = ref(0),
	selectedId = ref(null),
	panel = ref("Elements");
const selectedFieldId = ref(null);
const selectedField = computed(() =>
	props.fields.find((f) => f.field_key === selectedFieldId.value),
);
const types = ["Heading", "Text", "Image", "Table", "Divider", "Video link"];
const page = computed(() => props.modelValue.pages[current.value] || props.modelValue.pages[0]);
const selected = computed(() => page.value.blocks.find((b) => b.id === selectedId.value));
const history = ref([]),
	future = ref([]),
	error = ref("");
function snapshot() {
	return JSON.stringify({ data: props.modelValue, fields: props.fields });
}
function remember() {
	history.value.push(snapshot());
	if (history.value.length > 40) history.value.shift();
	future.value = [];
}
function restore(frame) {
	const value = JSON.parse(frame);
	emit("update:modelValue", value.data);
	emit("update:fields", value.fields);
	current.value = 0;
	selectedId.value = null;
	selectedFieldId.value = null;
}
function change(fn) {
	const data = JSON.parse(JSON.stringify(props.modelValue));
	remember();
	fn(data);
	emit("update:modelValue", data);
}
function undo() {
	if (!history.value.length) return;
	future.value.push(snapshot());
	restore(history.value.pop());
}
function redo() {
	if (!future.value.length) return;
	history.value.push(snapshot());
	restore(future.value.pop());
}
function add(type, x = 48, y = null) {
	if (y === null)
		y = Math.min(640, Math.max(24, ...page.value.blocks.map((b) => b.y + b.height)) + 24);
	selectedFieldId.value = null;
	const id = crypto.randomUUID();
	const text =
		type === "Heading"
			? "Document heading"
			: type === "Table"
				? "Column 1\tColumn 2\nValue\tValue"
				: type === "Video link"
					? "Watch video: https://example.com/video"
					: "Add your text here.";
	change((d) =>
		d.pages[current.value].blocks.push({
			id,
			type,
			text,
			x: Math.min(x, 95),
			y: Math.min(y, 640),
			width: 500,
			height: type === "Heading" ? 60 : type === "Divider" ? 15 : 150,
			font_size: type === "Heading" ? 28 : 12,
			color: "#24362d",
			background: "#ffffff",
		}),
	);
	selectedId.value = id;
}
function update(key, value) {
	change((d) => {
		const b = d.pages[current.value].blocks.find((b) => b.id === selectedId.value);
		b[key] = value;
	});
}
function remove() {
	change((d) => {
		d.pages[current.value].blocks = d.pages[current.value].blocks.filter(
			(b) => b.id !== selectedId.value,
		);
	});
	selectedId.value = null;
}
function duplicate() {
	change((d) => {
		const b = d.pages[current.value].blocks.find((b) => b.id === selectedId.value);
		d.pages[current.value].blocks.push({
			...b,
			id: crypto.randomUUID(),
			y: Math.min(842 - b.height, b.y + 20),
		});
	});
}
function addPage() {
	if (props.modelValue.pages.length >= 20) return;
	change((d) => d.pages.push({ blocks: [] }));
	current.value = props.modelValue.pages.length;
	selectedId.value = null;
}
function movePage(delta) {
	const to = current.value + delta;
	if (to < 0 || to >= props.modelValue.pages.length) return;
	change((d) => {
		[d.pages[to], d.pages[current.value]] = [d.pages[current.value], d.pages[to]];
	});
	emit(
		"update:fields",
		props.fields.map((f) => ({
			...f,
			page:
				f.page === current.value + 1
					? to + 1
					: f.page === to + 1
						? current.value + 1
						: f.page,
		})),
	);
	current.value = to;
	selectedId.value = null;
}
function deletePage() {
	if (props.modelValue.pages.length === 1) return;
	change((d) => d.pages.splice(current.value, 1));
	emit(
		"update:fields",
		props.fields
			.filter((f) => f.page !== current.value + 1)
			.map((f) => ({ ...f, page: f.page > current.value + 1 ? f.page - 1 : f.page })),
	);
	current.value = 0;
	selectedId.value = null;
}
function drop(e) {
	const type = e.dataTransfer.getData("text/plain");
	if (!types.includes(type) && !type.startsWith("field:")) return;
	if (props.backgroundUrl && !type.startsWith("field:")) return;
	const rect = e.currentTarget.getBoundingClientRect();
	const x = ((e.clientX - rect.left) * 595) / rect.width,
		y = ((e.clientY - rect.top) * 842) / rect.height;
	if (type.startsWith("field:")) addSigningField(type.slice(6), x, y);
	else add(type, x, y);
}
let drag = null,
	dragFrame = 0;
function dragPosition(e, m) {
	const sx = m.scale,
		sy = m.scaleY || m.scale;
	const width = m.field ? m.width * 595 : m.width,
		height = m.field ? m.height * 842 : m.height;
	return {
		x: Math.max(0, Math.min(595 - width, m.bx + (e.clientX - m.x) * sx)),
		y: Math.max(0, Math.min(842 - height, m.by + (e.clientY - m.y) * sy)),
	};
}
function move(e) {
	if (!drag) return;
	e.preventDefault();
	const m = drag,
		pos = dragPosition(e, m);
	m.latest = pos;
	if (dragFrame) return;
	dragFrame = requestAnimationFrame(() => {
		dragFrame = 0;
		if (drag !== m) return;
		m.element.style.transform = `translate3d(${(m.latest.x - m.bx) / m.scale}px,${(m.latest.y - m.by) / (m.scaleY || m.scale)}px,0)`;
	});
}
function clearDragVisual() {
	cancelAnimationFrame(dragFrame);
	dragFrame = 0;
	if (drag?.element) {
		drag.element.style.transform = "";
		drag.element.style.willChange = "";
		drag.element.style.zIndex = "";
	}
}
function cancelDrag() {
	clearDragVisual();
	drag = null;
}
onBeforeUnmount(cancelDrag);
function capture(e) {
	drag.element = e.currentTarget.closest(".builder-block,.builder-signing-field");
	drag.element.style.willChange = "transform";
	drag.element.style.zIndex = "10";
	e.currentTarget.setPointerCapture(e.pointerId);
}

function start(e, b) {
	if (e.button !== 0) return;
	selectedId.value = b.id;
	selectedFieldId.value = null;
	const rect = e.currentTarget.closest(".builder-page").getBoundingClientRect();
	drag = {
		id: b.id,
		x: e.clientX,
		y: e.clientY,
		bx: b.x,
		by: b.y,
		width: b.width,
		height: b.height,
		scale: 595 / rect.width,
		scaleY: 842 / rect.height,
	};
	capture(e);
}
function end(e) {
	if (!drag) return;
	const m = drag,
		pos = dragPosition(e, m);
	clearDragVisual();
	drag = null;
	if (Math.abs(pos.x - m.bx) < 0.1 && Math.abs(pos.y - m.by) < 0.1) return;
	if (m.field) {
		setSigningField({ pos_x: pos.x / 595, pos_y: pos.y / 842 });
		return;
	}
	change((d) => {
		const block = d.pages[current.value].blocks.find((b) => b.id === m.id);
		block.x = Math.round(pos.x);
		block.y = Math.round(pos.y);
	});
}
async function imageFile(e) {
	error.value = "";
	const file = e.target.files?.[0];
	if (!file) return;
	if (!["image/png", "image/jpeg"].includes(file.type) || file.size > 2 * 1024 * 1024) {
		error.value = "Choose a PNG or JPG smaller than 2 MB.";
		return;
	}
	const reader = new FileReader();
	reader.onload = () => update("image", reader.result);
	reader.readAsDataURL(file);
}

function addSigningField(type, x = 70, y = 500) {
	if (!fieldTypes.includes(type)) return;
	const f = {
		field_key: crypto.randomUUID(),
		field_type: type,
		label: type,
		page: current.value + 1,
		pos_x: Math.max(0, Math.min(0.7, x / 595)),
		pos_y: Math.max(0, Math.min(0.92, y / 842)),
		width: type === "Checkbox" ? 0.04 : 0.28,
		height: type === "Signature" ? 0.075 : 0.045,
		required: 1,
		font_size: 12,
		signer_role: props.recipients[0]?.role_key || "",
	};
	remember();
	emit("update:fields", [...props.fields, f]);
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
function moveSigningField(e, f) {
	if (e.button !== 0) return;
	selectedFieldId.value = f.field_key;
	selectedId.value = null;
	const rect = e.currentTarget.closest(".builder-page").getBoundingClientRect();
	drag = {
		field: true,
		id: f.field_key,
		x: e.clientX,
		y: e.clientY,
		bx: f.pos_x * 595,
		by: f.pos_y * 842,
		scaleY: 842 / rect.height,
		width: f.width,
		height: f.height,
		scale: 595 / rect.width,
	};
	capture(e);
}
function repeatSigningField() {
	error.value = "";
	try {
		const all = props.fields.map((f) => ({ ...f }));
		const f = all.find((f) => f.field_key === selectedFieldId.value);
		const copies = repeatField(f, pageCount.value, all);
		emit("update:fields", [...all, ...copies]);
	} catch (e) {
		error.value = e.message;
	}
}
</script>
<template>
	<div class="builder-workspace">
		<aside class="builder-library">
			<slot v-if="['Recipients', 'Email', 'Settings'].includes(activePanel)" name="panel" />
			<template v-else>
				<div class="editor-tabs">
					<button
						v-for="name in ['Elements', 'Pages']"
						:class="{ active: panel === name }"
						@click="panel = name"
					>
						{{ name }}
					</button>
				</div>
				<template v-if="panel === 'Elements'"
					><h2>Add an element</h2>
					<p class="muted">Drag onto the page or click to add.</p>
					<div v-if="!backgroundUrl && activePanel !== 'Fields'" class="block-palette">
						<button
							v-for="type in types"
							draggable="true"
							@dragstart="$event.dataTransfer.setData('text/plain', type)"
							@click="add(type)"
						>
							<span aria-hidden="true">{{
								{
									Heading: "H",
									Text: "T",
									Image: "▧",
									Table: "▦",
									Divider: "—",
									"Video link": "▷",
								}[type]
							}}</span
							>{{ type }}
						</button>
					</div>
					<h3>Signing fields</h3>
					<div class="block-palette signing-palette">
						<button
							v-for="type in fieldTypes"
							draggable="true"
							@dragstart="$event.dataTransfer.setData('text/plain', 'field:' + type)"
							@click="addSigningField(type)"
						>
							{{ type }}
						</button>
					</div>
					<small v-if="!backgroundUrl"
						>Video links appear as text in the signed PDF.</small
					></template
				>
				<template v-else
					><h2>Pages</h2>
					<button
						class="full"
						@click="addPage"
						:disabled="!!backgroundUrl || modelValue.pages.length >= 20"
					>
						+ Add page</button
					><button
						v-for="(p, i) in Array.from(
							{ length: pageCount },
							(_, i) => modelValue.pages[i] || { blocks: [] },
						)"
						:class="['page-thumbnail', { active: i === current }]"
						@click="
							current = i;
							selectedId = null;
						"
					>
						Page {{ i + 1 }}<small>{{ p.blocks.length }} elements</small>
					</button>
					<div class="button-group">
						<button @click="movePage(-1)" :disabled="!!backgroundUrl || current === 0">
							Move up</button
						><button
							@click="movePage(1)"
							:disabled="!!backgroundUrl || current === modelValue.pages.length - 1"
						>
							Move down
						</button>
					</div>
					<button
						@click="deletePage"
						:disabled="!!backgroundUrl || modelValue.pages.length === 1"
					>
						Remove page
					</button></template
				>
			</template>
		</aside>
		<div class="builder-canvas">
			<div class="builder-canvas-toolbar">
				<span
					>Page {{ current + 1 }} of {{ pageCount
					}}{{ backgroundUrl ? "" : " · A4" }}</span
				>
				<div class="button-group">
					<button @click="undo" :disabled="!history.length">Undo</button
					><button @click="redo" :disabled="!future.length">Redo</button>
				</div>
			</div>
			<div
				:class="['builder-page', { 'imported-page': backgroundUrl }]"
				@dragover.prevent
				@drop.prevent="drop"
			>
				<PdfPage
					v-if="backgroundUrl"
					:url="backgroundUrl"
					:page="current + 1"
					@loaded="
						importedCount = $event;
						$emit('page-count', $event);
					"
				/>
				<div
					v-for="b in backgroundUrl ? [] : page.blocks"
					:key="b.id"
					:class="['builder-block', { selected: b.id === selectedId }]"
					:style="{
						left: (b.x / 595) * 100 + '%',
						top: (b.y / 842) * 100 + '%',
						width: (b.width / 595) * 100 + '%',
						height: (b.height / 842) * 100 + '%',
						background: b.background,
						color: b.color,
						fontSize: b.font_size + 'px',
					}"
					@click="
						selectedId = b.id;
						selectedFieldId = null;
					"
				>
					<button
						class="block-handle"
						:aria-label="'Move ' + b.type"
						@pointerdown="start($event, b)"
						@pointermove="move"
						@pointerup="end"
						@pointercancel="cancelDrag"
					>
						⠿
					</button>
					<button
						class="block-select"
						@pointerdown="start($event, b)"
						@pointermove="move"
						@pointerup="end"
						@pointercancel="cancelDrag"
						:aria-label="'Edit ' + b.type"
						@click="
							selectedId = b.id;
							selectedFieldId = null;
						"
					></button>
					<img
						v-if="b.type === 'Image' && b.image"
						:src="b.image"
						alt="Document image"
					/>
					<span v-else-if="b.type === 'Image'" class="image-placeholder"
						>Choose an image in Properties</span
					>
					<hr v-else-if="b.type === 'Divider'" />
					<table v-else-if="b.type === 'Table'">
						<tr v-for="line in b.text.split('\n')">
							<td v-for="cell in line.split('\t')">{{ cell }}</td>
						</tr>
					</table>
					<div
						v-else
						:style="{
							fontWeight: b.type === 'Heading' ? 700 : 400,
							whiteSpace: 'pre-wrap',
						}"
					>
						{{ b.text }}
					</div>
				</div>
				<button
					v-for="f in fields.filter((f) => f.page === current + 1)"
					:key="f.field_key"
					:class="[
						'builder-signing-field',
						{ selected: f.field_key === selectedFieldId },
					]"
					:style="{
						left: f.pos_x * 100 + '%',
						top: f.pos_y * 100 + '%',
						width: f.width * 100 + '%',
						height: f.height * 100 + '%',
					}"
					@pointerdown="moveSigningField($event, f)"
					@pointermove="move"
					@pointerup="end"
					@pointercancel="cancelDrag"
					@click="
						selectedFieldId = f.field_key;
						selectedId = null;
					"
				>
					{{ f.label || f.field_type }}<span v-if="f.required"> *</span>
				</button>
				<p
					v-if="
						!backgroundUrl &&
						!page.blocks.length &&
						!fields.some((f) => f.page === current + 1)
					"
					class="builder-empty"
				>
					Drop an element here to start your document.
				</p>
			</div>
		</div>
		<aside v-if="selected" class="builder-properties">
			<div class="dialog-heading">
				<h2>Properties</h2>
				<button @click="selectedId = null" aria-label="Close properties">×</button>
			</div>
			<p>{{ selected.type }}</p>
			<label v-if="selected.type === 'Image'"
				>Image<input type="file" accept="image/png,image/jpeg" @change="imageFile"
			/></label>
			<label v-else-if="selected.type !== 'Divider'"
				>{{ selected.type === "Table" ? "Rows (tab-separated columns)" : "Content"
				}}<textarea
					:value="selected.text"
					rows="7"
					@change="update('text', $event.target.value)"
				/>
			</label>
			<p v-if="error" role="alert" class="error">{{ error }}</p>
			<div class="property-grid">
				<label v-for="key in ['x', 'y', 'width', 'height', 'font_size']"
					>{{
						{
							x: "Left",
							y: "Top",
							width: "Width",
							height: "Height",
							font_size: "Font size",
						}[key]
					}}<input
						type="number"
						:value="selected[key]"
						min="0"
						@change="update(key, Number($event.target.value))" /></label
				><label
					>Text color<input
						type="color"
						:value="selected.color"
						@input="update('color', $event.target.value)" /></label
				><label
					>Background<input
						type="color"
						:value="selected.background"
						@input="update('background', $event.target.value)"
				/></label>
			</div>
			<div class="button-group">
				<button @click="duplicate">Duplicate</button
				><button @click="remove">Delete element</button>
			</div>
		</aside>
		<aside v-if="selectedField" class="builder-properties">
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
				<label v-for="key in ['pos_x', 'pos_y', 'width', 'height']"
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
						@change="setSigningField({ [key]: Number($event.target.value) / 100 })"
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
			<button
				@click="
					$emit('update:fields', [
						...fields,
						{ ...selectedField, field_key: crypto.randomUUID() },
					])
				"
			>
				Duplicate field
			</button>
			<button
				@click="
					$emit(
						'update:fields',
						fields.filter((f) => f.field_key !== selectedFieldId),
					);
					selectedFieldId = null;
				"
			>
				Delete field
			</button>
		</aside>
		<aside v-if="!selected && !selectedField" class="builder-properties properties-empty">
			<h2>Properties</h2>
			<p>Select an element or signing field to edit its details.</p>
		</aside>
	</div>
</template>
