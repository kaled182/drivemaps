# ... (imports e outras funções)

# Remova ou comente a função registro_unico se você quiser permitir múltiplos IDs de ordem diferentes
# ou adapte-a para levar em conta o prefixo no order_number, se necessário.
# Por enquanto, vamos manter a lógica de registro_unico como está, que compara endereço e CEP.

@main_routes.route('/import_planilha', methods=['POST'])
def import_planilha():
    try:
        if request.content_length > TAMANHO_MAXIMO:
            logger.warning(f"Tentativa de upload de arquivo muito grande: {request.content_length} bytes")
            return jsonify({"success": False, "msg": "Arquivo muito grande (máx. 5MB)"}), 400

        file = request.files.get('planilha')
        empresa = request.form.get('empresa', '').lower()
        
        if not file or not empresa:
            logger.warning("Arquivo ou empresa não especificados na importação.")
            return jsonify({"success": False, "msg": "Arquivo ou empresa não especificados"}), 400
            
        if not arquivo_seguro(file):
            logger.warning(f"Tipo de arquivo não permitido ou inválido: {file.filename}")
            return jsonify({"success": False, "msg": "Tipo de arquivo não permitido ou inválido"}), 400

        lista_atual = session.get('lista', [])
        logger.info(f"Lista atual antes da importação: {len(lista_atual)} itens.")

        try:
            novos_itens_importados = [] # Lista temporária para os novos itens

            if empresa == "delnext":
                file.seek(0)
                filename = file.filename.lower()
                
                if filename.endswith(('.xlsx', '.xls')):
                    logger.info("Processando arquivo Delnext como Excel.")
                    df = pd.read_excel(file, header=1)
                elif filename.endswith(('.csv', '.txt')):
                    logger.info("Processando arquivo Delnext como CSV/TXT.")
                    try:
                        content = file.read().decode('utf-8')
                        dialect = csv.Sniffer().sniff(content.splitlines()[0], delimiters=[',', ';'])
                        file.seek(0)
                        df = pd.read_csv(io.StringIO(content), header=1, sep=dialect.delimiter)
                    except Exception as csv_err:
                        logger.warning(f"Erro ao tentar detectar separador CSV, tentando padrão: {csv_err}")
                        file.seek(0)
                        df = pd.read_csv(file, header=1, sep=',')
                        if df.empty or 'morada' not in df.columns.str.lower() and 'código postal' not in df.columns.str.lower():
                            logger.warning("Leitura CSV com vírgula falhou ou colunas não encontradas, tentando ponto e vírgula.")
                            file.seek(0)
                            df = pd.read_csv(file, header=1, sep=';')
                else:
                    return jsonify({
                        "success": False,
                        "msg": "Formato de arquivo Delnext não suportado. Use .xlsx, .xls, .csv ou .txt"
                    }), 400
                
                if df.empty:
                    return jsonify({
                        "success": False,
                        "msg": "A planilha está vazia ou o formato é inválido após ignorar a primeira linha."
                    }), 400

                df.columns = df.columns.astype(str)
                
                col_morada = next((c for c in df.columns if 'morada' in c.lower()), None)
                col_cep = next((c for c in df.columns if 'código postal' in c.lower() or 'codigo postal' in c.lower()), None)
                
                if not col_morada or not col_cep:
                    logger.error(f"Colunas 'Morada' ou 'Código Postal' não encontradas no arquivo Delnext. Colunas disponíveis: {df.columns.tolist()}")
                    return jsonify({
                        "success": False,
                        "msg": "Estrutura inválida. A planilha Delnext deve conter colunas de 'Morada' e 'Código Postal' (ignorando maiúsculas/minúsculas)."
                    }), 400
                
                # Encontrar o último order_number para Delnext para continuar a sequência
                # Filtrar os order_numbers que começam com 'D' e converter para int para encontrar o máximo
                last_delnext_order_num = 0
                for item in lista_atual:
                    if item.get('importacao_tipo') == 'delnext' and item.get('order_number', '').startswith('D'):
                        try:
                            num = int(item['order_number'][1:]) # Pega o número após o 'D'
                            if num > last_delnext_order_num:
                                last_delnext_order_num = num
                        except ValueError:
                            continue # Ignora se não for um número válido após 'D'


                for index, row in df.iterrows():
                    endereco = str(row[col_morada]).strip()
                    cep = str(row[col_cep]).strip()
                    
                    if not endereco or not cep:
                        logger.warning(f"Linha {index+2} (após cabeçalho) ignorada por conter endereço ou CEP vazio: Endereço='{endereco}', CEP='{cep}'")
                        continue 
                        
                    cep = re.sub(r'[^\d-]', '', cep)
                    if len(cep) == 8 and '-' not in cep:
                        cep = f"{cep[:4]}-{cep[4:]}"
                    elif len(cep) == 7 and '-' not in cep:
                        cep = f"{cep[:4]}-{cep[4:]}"
                    elif len(cep) == 9 and cep.count('-') == 1:
                        cep = cep[:8]
                    
                    logger.info(f"Processando linha {index+2}: Endereço='{endereco}', CEP formatado='{cep}'")
                    
                    res_google = valida_rua_google_cache(endereco, cep)
                    rua_digitada = endereco.split(',')[0] if endereco else ''
                    rua_google = res_google.get('route_encontrada', '')
                    
                    rua_bate = (normalizar(rua_digitada) in normalizar(rua_google) or 
                                  normalizar(rua_google) in normalizar(rua_digitada))
                    cep_ok = (cep == res_google.get('postal_code_encontrado', ''))
                    
                    novo = {
                        # Aumenta o contador para Delnext e adiciona o prefixo 'D'
                        "order_number": "", # Será preenchido após a verificação de duplicidade
                        "address": endereco,
                        "cep": cep,
                        "status_google": res_google.get('status'),
                        "postal_code_encontrado": res_google.get('postal_code_encontrado', ''),
                        "endereco_formatado": res_google.get('endereco_formatado', ''),
                        "latitude": res_google.get('coordenadas', {}).get('lat', ''),
                        "longitude": res_google.get('coordenadas', {}).get('lng', ''),
                        "rua_google": rua_google,
                        "cep_ok": cep_ok,
                        "rua_bate": rua_bate,
                        "freguesia": res_google.get('sublocality', ''),
                        "importacao_tipo": "delnext",
                        "cor": cor_por_tipo("delnext")
                    }
                    
                    if registro_unico(lista_atual, novo):
                        novos_itens_importados.append(novo) # Adiciona à lista temporária
                    else:
                        logger.info(f"Registro duplicado ignorado: {endereco}, {cep}")

            elif empresa == "paack":
                file.seek(0)
                filename = file.filename.lower()
                
                # Adaptação para Paack (assumindo CSV ou Excel com colunas Endereço e CEP)
                if filename.endswith(('.xlsx', '.xls')):
                    logger.info("Processando arquivo Paack como Excel.")
                    df = pd.read_excel(file, header=0) # Paack pode ter header=0 ou outro
                elif filename.endswith(('.csv', '.txt')):
                    logger.info("Processando arquivo Paack como CSV/TXT.")
                    try:
                        content = file.read().decode('utf-8')
                        dialect = csv.Sniffer().sniff(content.splitlines()[0], delimiters=[',', ';'])
                        file.seek(0)
                        df = pd.read_csv(io.StringIO(content), header=0, sep=dialect.delimiter)
                    except Exception as csv_err:
                        logger.warning(f"Erro ao tentar detectar separador CSV, tentando padrão para Paack: {csv_err}")
                        file.seek(0)
                        df = pd.read_csv(file, header=0, sep=',')
                        if df.empty or 'endereco' not in df.columns.str.lower() and 'cep' not in df.columns.str.lower():
                            logger.warning("Leitura CSV Paack com vírgula falhou ou colunas não encontradas, tentando ponto e vírgula.")
                            file.seek(0)
                            df = pd.read_csv(file, header=0, sep=';')
                else:
                     return jsonify({
                        "success": False,
                        "msg": "Formato de arquivo Paack não suportado. Use .xlsx, .xls, .csv ou .txt"
                    }), 400

                if df.empty:
                    return jsonify({
                        "success": False,
                        "msg": "A planilha Paack está vazia ou o formato é inválido."
                    }), 400
                
                df.columns = df.columns.astype(str)
                col_end = next((c for c in df.columns if 'endereco' in c.lower()), None)
                col_cep = next((c for c in df.columns if 'cep' in c.lower()), None)
                
                if not col_end or not col_cep:
                    logger.error(f"Colunas 'Endereço' ou 'CEP' não encontradas no arquivo Paack. Colunas disponíveis: {df.columns.tolist()}")
                    return jsonify({"success": False, "msg": "Colunas 'Endereço' e 'CEP' não encontradas na planilha Paack"}), 400

                # Encontrar o último order_number para Paack para continuar a sequência
                last_paack_order_num = 0
                for item in lista_atual:
                    if item.get('importacao_tipo') == 'paack' and item.get('order_number', '').startswith('P'):
                        try:
                            num = int(item['order_number'][1:])
                            if num > last_paack_order_num:
                                last_paack_order_num = num
                        except ValueError:
                            continue

                for index, row in df.iterrows():
                    endereco = str(row[col_end]).strip()
                    cep = str(row[col_cep]).strip()

                    if not endereco or not cep:
                        logger.warning(f"Linha {index+1} (Paack) ignorada por conter endereço ou CEP vazio: Endereço='{endereco}', CEP='{cep}'")
                        continue

                    cep = re.sub(r'[^\d-]', '', cep)
                    if len(cep) == 8 and '-' not in cep:
                        cep = f"{cep[:4]}-{cep[4:]}"
                    elif len(cep) == 7 and '-' not in cep:
                        cep = f"{cep[:4]}-{cep[4:]}"
                    elif len(cep) == 9 and cep.count('-') == 1:
                        cep = cep[:8]

                    logger.info(f"Processando linha {index+1} (Paack): Endereço='{endereco}', CEP formatado='{cep}'")

                    res_google = valida_rua_google_cache(endereco, cep)
                    rua_digitada = endereco.split(',')[0] if endereco else ''
                    rua_google = res_google.get('route_encontrada', '')
                    
                    rua_bate = (normalizar(rua_digitada) in normalizar(rua_google) or 
                                  normalizar(rua_google) in normalizar(rua_digitada))
                    cep_ok = (cep == res_google.get('postal_code_encontrado', ''))

                    novo = {
                        "order_number": "", # Será preenchido após a verificação de duplicidade
                        "address": endereco,
                        "cep": cep,
                        "status_google": res_google.get('status'),
                        "postal_code_encontrado": res_google.get('postal_code_encontrado', ''),
                        "endereco_formatado": res_google.get('endereco_formatado', ''),
                        "latitude": res_google.get('coordenadas', {}).get('lat', ''),
                        "longitude": res_google.get('coordenadas', {}).get('lng', ''),
                        "rua_google": rua_google,
                        "cep_ok": cep_ok,
                        "rua_bate": rua_bate,
                        "freguesia": res_google.get('sublocality', ''),
                        "importacao_tipo": "paack",
                        "cor": cor_por_tipo("paack")
                    }
                    
                    if registro_unico(lista_atual, novo):
                        novos_itens_importados.append(novo)
                    else:
                        logger.info(f"Registro duplicado Paack ignorado: {endereco}, {cep}")

            else:
                return jsonify({"success": False, "msg": "Empresa não suportada"}), 400

            # --- Lógica de atribuição de order_number e adição à lista principal ---
            # Primeiro, adiciona todos os novos itens válidos à lista atual
            lista_atual.extend(novos_itens_importados)

            # Depois, re-atribui os order_numbers para cada tipo, mantendo a sequência
            # Resetar contadores
            manual_counter = 0
            delnext_counter = 0
            paack_counter = 0

            # Encontrar o maior número atual para cada tipo de importação
            for item in lista_atual:
                order_num_str = str(item.get('order_number', ''))
                try:
                    if item.get('importacao_tipo') == 'manual' and order_num_str.isdigit():
                        manual_counter = max(manual_counter, int(order_num_str))
                    elif item.get('importacao_tipo') == 'delnext' and order_num_str.startswith('D') and order_num_str[1:].isdigit():
                        delnext_counter = max(delnext_counter, int(order_num_str[1:]))
                    elif item.get('importacao_tipo') == 'paack' and order_num_str.startswith('P') and order_num_str[1:].isdigit():
                        paack_counter = max(paack_counter, int(order_num_str[1:]))
                except ValueError:
                    pass # Ignora order_numbers mal formatados

            # Atribui novos order_numbers
            for item in lista_atual:
                if item.get('order_number') == "": # Apenas para itens sem order_number atribuído (novos)
                    if item.get('importacao_tipo') == 'manual':
                        manual_counter += 1
                        item['order_number'] = str(manual_counter)
                    elif item.get('importacao_tipo') == 'delnext':
                        delnext_counter += 1
                        item['order_number'] = f"D{delnext_counter}"
                    elif item.get('importacao_tipo') == 'paack':
                        paack_counter += 1
                        item['order_number'] = f"P{paack_counter}"
                # Para itens já existentes na lista, seus order_numbers são mantidos
                # (a menos que a lógica de reindexação total seja desejada, que não é o caso aqui)


            origens = list({item.get('importacao_tipo', 'manual') for item in lista_atual})
            session['lista'] = lista_atual
            session.modified = True
            logger.info(f"Importação concluída. Total de itens na sessão: {len(lista_atual)}. Origens: {origens}")
            
            return jsonify({
                "success": True,
                "lista": lista_atual,
                "origens": origens,
                "total": len(lista_atual)
            })

        except Exception as e:
            logger.error(f"Erro ao processar arquivo durante a importação: {str(e)}", exc_info=True)
            return jsonify({"success": False, "msg": f"Erro ao processar arquivo: {str(e)}"}), 500

    except Exception as e:
        logger.error(f"Erro geral na importação (antes do processamento do arquivo): {str(e)}", exc_info=True)
        return jsonify({"success": False, "msg": f"Erro na importação: {str(e)}"}), 500


@main_routes.route('/preview', methods=['POST'])
def preview():
    try:
        # A lógica de preview deve ser mais inteligente para order_numbers.
        # No preview, ao adicionar manual, o order_number deve ser sequencial numérico simples.
        # Ajuste esta parte para que ele apenas adicione números simples.
        # E a re-enumeração final abaixo tratará de todos os order_numbers.

        if 'preview_loaded' not in session:
            session.clear()
            session['lista'] = []
            session['preview_loaded'] = True
            session.modified = True

        enderecos_brutos = request.form.get('enderecos', '')
        if not enderecos_brutos.strip():
            raise ValueError("Nenhum endereço fornecido")

        regex_cep = re.compile(r'(\d{4}-\d{3})')
        linhas = [linha.strip() for linha in enderecos_brutos.split('\n') if linha.strip()]
        lista_preview_novos = [] # Itens a serem adicionados pelo preview

        i = 0
        while i < len(linhas) - 2:
            linha = linhas[i]
            cep_match = regex_cep.search(linha)
            if cep_match:
                if i + 2 < len(linhas) and linhas[i+2] == linha:
                    numero_pacote_str = linhas[i+3] if (i+3) < len(linhas) else ""
                    # Se o numero_pacote_str for um número válido, use-o, senão será vazio e o re-indexador no final irá atribuir.
                    numero_pacote = numero_pacote_str if numero_pacote_str.isdigit() else "" 

                    cep = cep_match.group(1)
                    res_google = valida_rua_google_cache(linha, cep)
                    
                    rua_digitada = linha.split(',')[0] if linha else ''
                    rua_google = res_google.get('route_encontrada', '')
                    rua_bate = (normalizar(rua_digitada) in normalizar(rua_google) or 
                              normalizar(rua_google) in normalizar(rua_digitada))
                    cep_ok = cep == res_google.get('postal_code_encontrado', '')
                    
                    novo = {
                        "order_number": numero_pacote, # Pode ser o número digitado ou vazio para re-indexar
                        "address": linha,
                        "cep": cep,
                        "status_google": res_google.get('status'),
                        "postal_code_encontrado": res_google.get('postal_code_encontrado', ''),
                        "endereco_formatado": res_google.get('endereco_formatado', ''),
                        "latitude": res_google.get('coordenadas', {}).get('lat', ''),
                        "longitude": res_google.get('coordenadas', {}).get('lng', ''),
                        "rua_google": rua_google,
                        "cep_ok": cep_ok,
                        "rua_bate": rua_bate,
                        "freguesia": res_google.get('sublocality', ''),
                        "importacao_tipo": "manual",
                        "cor": cor_por_tipo("manual")
                    }
                    
                    if registro_unico(session.get('lista', []) + lista_preview_novos, novo): # Verifica duplicidade na lista atual + novos do preview
                        lista_preview_novos.append(novo)
                    i += 4
                else:
                    i += 1
            else:
                i += 1
        
        lista_atual = session.get('lista', [])
        lista_atual.extend(lista_preview_novos) # Adiciona os novos itens do preview

        # --- Lógica de re-atribuição de order_number para toda a lista ---
        # Este bloco é o mesmo da import_planilha, para garantir consistência.
        manual_counter = 0
        delnext_counter = 0
        paack_counter = 0

        for item in lista_atual:
            order_num_str = str(item.get('order_number', ''))
            try:
                if item.get('importacao_tipo') == 'manual' and order_num_str.isdigit():
                    manual_counter = max(manual_counter, int(order_num_str))
                elif item.get('importacao_tipo') == 'delnext' and order_num_str.startswith('D') and order_num_str[1:].isdigit():
                    delnext_counter = max(delnext_counter, int(order_num_str[1:]))
                elif item.get('importacao_tipo') == 'paack' and order_num_str.startswith('P') and order_num_str[1:].isdigit():
                    paack_counter = max(paack_counter, int(order_num_str[1:]))
            except ValueError:
                pass

        # Atribui novos order_numbers
        for item in lista_atual:
            # Se o item não tem order_number (ex: recém-adicionado manual, ou importado com order_number vazio)
            # OU se o order_number não corresponde ao padrão do tipo (ex: 'D1' em manual),
            # re-atribui.
            needs_reindex = False
            if item.get('importacao_tipo') == 'manual':
                if not str(item.get('order_number', '')).isdigit(): # Se não é um número simples
                    needs_reindex = True
            elif item.get('importacao_tipo') == 'delnext':
                if not str(item.get('order_number', '')).startswith('D'): # Se não começa com 'D'
                    needs_reindex = True
            elif item.get('importacao_tipo') == 'paack':
                if not str(item.get('order_number', '')).startswith('P'): # Se não começa com 'P'
                    needs_reindex = True

            if needs_reindex:
                if item.get('importacao_tipo') == 'manual':
                    manual_counter += 1
                    item['order_number'] = str(manual_counter)
                elif item.get('importacao_tipo') == 'delnext':
                    delnext_counter += 1
                    item['order_number'] = f"D{delnext_counter}"
                elif item.get('importacao_tipo') == 'paack':
                    paack_counter += 1
                    item['order_number'] = f"P{paack_counter}"
            # Se o order_number já está no formato correto para o tipo, ele é mantido.

        session['lista'] = lista_atual
        session.modified = True
        
        return render_template(
            "preview.html",
            lista=lista_atual,
            GOOGLE_API_KEY=os.environ.get("GOOGLE_API_KEY", ""),
            CORES_IMPORTACAO=CORES_IMPORTACAO,
            origens=list({item.get('importacao_tipo', 'manual') for item in lista_atual})
        )
    except Exception as e:
        logger.error(f"Erro no preview: {str(e)}", exc_info=True)
        return jsonify({"success": False, "msg": f"Erro: {str(e)}"}), 500

# ... (restante do código)

@main_routes.route('/generate', methods=['POST'])
def generate():
    try:
        global csv_content
        total = int(request.form['total'])
        lista = []
        
        for i in range(total):
            item = {
                "order_number": request.form.get(f'numero_pacote_{i}', ''),
                "address": request.form.get(f'endereco_{i}', ''),
                "cep": request.form.get(f'cep_{i}', ''),
                "importacao_tipo": request.form.get(f'importacao_tipo_{i}', 'manual'),
                "cor": request.form.get(f'cor_{i}', CORES_IMPORTACAO[0])
            }
            
            # Recupere os dados completos do item da sessão para garantir que latitude/longitude, etc.
            # já foram validados e estão presentes. Se não for feito aqui,
            # cada chamada a valida_rua_google_cache vai refazer a requisição.
            # O ideal é que o 'generate' pegue os dados JÁ VALIDADOS da sessão,
            # e não re-valide tudo aqui, a menos que seja para um último check.
            # Por agora, estou mantendo a chamada a valida_rua_google_cache como está,
            # mas é um ponto para otimização futura.

            # IMPORTANTE: Se os campos latitude/longitude e outros campos de validação Google
            # não estiverem sendo passados como hidden fields do HTML, eles não estarão
            # no `request.form`. O ideal é que a função `generate` use a `session['lista']`
            # diretamente, que já tem todos os dados validados.
            # Para isso, o `total` e a iteração `for i in range(total)` teriam que ser removidos,
            # e o loop seria `for item in session.get('lista', [])`.

            # MUDANÇA RECOMENDADA: Usar session['lista'] diretamente aqui
            # para garantir que os dados já validados (lat/lng, status, etc.) sejam usados.
            # Remova o loop `for i in range(total)` e substitua por:
            # lista_para_csv = session.get('lista', [])

            # PORÉM, para manter a consistência com o seu request.form atual,
            # estou assumindo que os campos de lat/lng/status_google, etc.
            # **NÃO SÃO** passados no formulário. Se eles não são, então
            # a chamada a `valida_rua_google_cache` aqui é necessária para o CSV.
            # Se eles SÃO passados, o ideal é não re-validar e pegar do request.form
            # ou, melhor ainda, da session['lista'].

            # Para manter o mínimo de mudança e focar no order_number, vou deixar o
            # bloco abaixo de validação como está, mas tenha em mente o comentário acima.
            res_google = valida_rua_google_cache(item["address"], item["cep"])
            
            item.update({
                "status_google": res_google.get('status'),
                "postal_code_encontrado": res_google.get('postal_code_encontrado', ''),
                "latitude": res_google.get('coordenadas', {}).get('lat', ''),
                "longitude": res_google.get('coordenadas', {}).get('lng', ''),
                "rua_google": res_google.get('route_encontrada', ''),
                "cep_ok": item["cep"] == res_google.get('postal_code_encontrado', ''),
                "rua_bate": (normalizar(item["address"].split(',')[0]) in 
                           normalizar(res_google.get('route_encontrada', ''))) if item["address"] else False,
                "freguesia": res_google.get('sublocality', '')
            })
            
            lista.append(item)

        # Gerar CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Cabeçalho
        writer.writerow([
            "order number", "name", "address", "latitude", "longitude", 
            "duration", "start time", "end time", "phone", "contact", 
            "notes", "color", "Group", "rua_google", "freguesia_google", "status"
        ])
        
        # Dados
        for row in lista: # Esta lista `lista` agora conterá os order_numbers com prefixo 'D', 'P' ou números
            status = "Validado"
            if not row["cep_ok"]:
                status = "CEP divergente"
            elif not row["rua_bate"]:
                status = "Rua divergente"
                
            writer.writerow([
                row["order_number"], "", row["address"], 
                row["latitude"], row["longitude"], 
                "", "", "", "", "",
                row["postal_code_encontrado"] or row["cep"], 
                row["cor"], "", 
                row["rua_google"],
                row.get("freguesia", ""), 
                status
            ])
        
        csv_content = output.getvalue()
        return redirect(url_for('main.download'))
        
    except Exception as e:
        logger.error(f"Erro ao gerar CSV: {str(e)}", exc_info=True)
        return jsonify({"success": False, "msg": f"Erro ao gerar CSV: {str(e)}"}), 500
