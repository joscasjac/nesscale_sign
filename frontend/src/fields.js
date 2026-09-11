export const fieldTypes = [
	"Signature",
	"Initial",
	"Name",
	"Email",
	"Date Signed",
	"Text",
	"Checkbox",
	"Dropdown",
	"Label",
	"Stamp",
];
export function repeatField(field, pageCount, existing, makeId = () => crypto.randomUUID()) {
	if (!field || pageCount < 2) return [];
	const group = field.repeat_group || makeId();
	const copies = [];
	for (let page = 1; page <= pageCount; page++) {
		if (
			page === field.page ||
			existing.some((f) => f.repeat_group === group && f.page === page)
		)
			continue;
		copies.push({ ...field, name: undefined, field_key: makeId(), repeat_group: group, page });
	}
	if (existing.length + copies.length > 500)
		throw new Error("A document can contain at most 500 fields.");
	field.repeat_group = group;
	return copies;
}

export function nextRequiredField(fields, complete) {
	return (
		[...fields]
			.sort((a, b) => a.page - b.page || a.pos_y - b.pos_y || a.pos_x - b.pos_x)
			.find((field) => field.required && !complete(field)) || null
	);
}
