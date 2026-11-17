import { __ } from "./translation.js";
export function activeVariable(text, caret = text.length) {
	const before = text.slice(0, caret),
		start = before.lastIndexOf("{{");
	if (start < 0 || before.lastIndexOf("}}") > start || before.slice(start).includes("\n"))
		return null;
	return { start, query: before.slice(start + 2).trim() };
}
export function variableSuggestions(options, query = "") {
	return options
		.filter((o) => (o.key + " " + (o.label || "")).toLowerCase().includes(query.toLowerCase()))
		.slice(0, 8);
}
export function resolveVariables(text, variables) {
	return String(text || "").replace(/{{\s*([A-Za-z][A-Za-z0-9_.]*)\s*}}/g, (token, key) => {
		const value = variables.find((v) => v.key === key)?.value;
		return value === undefined || value === "" ? token : String(value);
	});
}
export function documentVariables(data, form = {}) {
	const first =
		form.signers?.find((s) => s.role_key === data.primaryRecipient) || form.signers?.[0] || {};
	return [
		{ key: "document.title", value: form.title || "", label: __("Document title") },
		{ key: "document.createdDate", value: data.createdDate || "", label: __("Created date") },
		{ key: "document.refNumber", value: data.refNumber || "", label: __("Reference number") },
		{ key: "contact.name", value: first.signer_name || "", label: __("Primary contact name") },
		{ key: "contact.email", value: first.signer_email || "", label: __("Primary contact email") },
		...(data.variables || []),
	];
}
