def modify_data(grupos_seleccionados, data) -> dict:
    if grupos_seleccionados is None:
        grupos_seleccionados = [data]

    elif data == "todos":
        if "todos" in grupos_seleccionados:
            grupos_seleccionados.remove(data)
        else:
            grupos_seleccionados = ["todos"]

    elif data in grupos_seleccionados:
        grupos_seleccionados.remove(data)

    else:
        if "todos" in grupos_seleccionados:
            grupos_seleccionados.remove("todos")
        grupos_seleccionados += [data]

    return grupos_seleccionados
